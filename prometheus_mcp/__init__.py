#!/usr/bin/env python

import sys
import json
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
import time
from datetime import datetime, timedelta

import requests
from mcp.server.fastmcp import FastMCP

# Initialize MCP
mcp = FastMCP("Prometheus MCP")

@dataclass
class PrometheusConfig:
    url: str
    # Optional credentials
    username: Optional[str] = None
    password: Optional[str] = None
    token: Optional[str] = None
    # Optional Org ID for multi-tenant setups
    org_id: Optional[str] = None
    # Query parameters
    timeout: int = 30
    limit: int = 1000

# This will be populated by parse_arguments in setup_environment
config: PrometheusConfig = None

def get_prometheus_auth():
    """Get authentication for Prometheus based on provided credentials."""
    if config.token:
        return {"Authorization": f"{config.token}"}
    elif config.username and config.password:
        return requests.auth.HTTPBasicAuth(config.username, config.password)
    return None

def make_prometheus_request(endpoint, params=None):
    """Make a request to the Prometheus API with proper authentication and headers."""
    if not config.url:
        raise ValueError("Prometheus configuration is missing. Please provide --url when starting the server.")

    url = f"{config.url.rstrip('/')}/api/v1/{endpoint}"
    auth = get_prometheus_auth()
    headers = {}

    if isinstance(auth, dict):  # Token auth is passed via headers
        headers.update(auth)
        auth = None  # Clear auth for requests.get if it's already in headers
    
    # Add OrgID header if specified
    if config.org_id:
        headers["X-Scope-OrgID"] = config.org_id

    # Make the request with appropriate headers and auth
    response = requests.get(url, params=params, auth=auth, headers=headers)
    
    response.raise_for_status()
    result = response.json()
    
    if result["status"] != "success":
        raise ValueError(f"Prometheus API error: {result.get('error', 'Unknown error')}")
    
    return result["data"]

@mcp.tool(description="Execute a PromQL instant query against Prometheus")
async def execute_query(query: str, time: Optional[str] = None, timeout: Optional[int] = None, 
                       limit: Optional[int] = None) -> Dict[str, Any]:
    """Execute an instant query against Prometheus.
    
    Args:
        query: PromQL query string
        time: Optional RFC3339 or Unix timestamp (default: current time)
        timeout: Evaluation timeout in seconds (default: 30s)
        limit: Maximum number of returned series (default: 1000)
        
    Returns:
        Query result with type (vector, matrix, scalar, string) and values
    """
    params = {"query": query}
    if time:
        params["time"] = time
    
    # Apply timeout and limit parameters
    if timeout is None:
        timeout = config.timeout
    if limit is None:
        limit = config.limit
    
    params["timeout"] = str(timeout)
    params["limit"] = str(limit)
    
    data = make_prometheus_request("query", params=params)
    return {
        "resultType": data["resultType"],
        "result": data["result"]
    }

@mcp.tool(description="Execute a PromQL range query with start time, end time, and step interval")
async def execute_range_query(query: str, start: str, end: str, step: str, 
                             timeout: Optional[int] = None, limit: Optional[int] = None) -> Dict[str, Any]:
    """Execute a range query against Prometheus.
    
    Args:
        query: PromQL query string
        start: Start time as RFC3339 or Unix timestamp
        end: End time as RFC3339 or Unix timestamp
        step: Query resolution step width (e.g., '15s', '1m', '1h')
        timeout: Evaluation timeout in seconds (default: 30s)
        limit: Maximum number of returned series (default: 1000)
        
    Returns:
        Range query result with type (usually matrix) and values over time
    """
    params = {
        "query": query,
        "start": start,
        "end": end,
        "step": step
    }
    
    # Apply timeout and limit parameters
    if timeout is None:
        timeout = config.timeout
    if limit is None:
        limit = config.limit
    
    params["timeout"] = str(timeout)
    params["limit"] = str(limit)
    
    data = make_prometheus_request("query_range", params=params)
    return {
        "resultType": data["resultType"],
        "result": data["result"]
    }

@mcp.tool(description="Get all alerting and recording rules currently loaded in Prometheus")
async def get_rules(type: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve alerting and recording rules that are currently loaded in Prometheus.
    
    Args:
        type: Optional filter to only return rules of a certain type ('alert' or 'recording')
        
    Returns:
        Dictionary containing groups of rules with their current state
    """
    params = {}
    if type:
        params["type"] = type
    
    data = make_prometheus_request("rules", params=params)
    return data

@mcp.tool(description="List all available metrics in Prometheus")
async def list_metrics() -> List[str]:
    """Retrieve a list of all metric names available in Prometheus.
    
    Returns:
        List of metric names as strings
    """
    data = make_prometheus_request("label/__name__/values")
    return data

@mcp.tool(description="List all available label names")
async def get_labels() -> List[str]:
    """Retrieve a list of all label names available in Prometheus.
    
    Returns:
        List of label names as strings
    """
    data = make_prometheus_request("labels")
    return data

@mcp.tool(description="Get all values for a specific label")
async def get_label_values(label: str) -> List[str]:
    """Retrieve all values for a given label name.
    
    Args:
        label: The name of the label to retrieve values for
        
    Returns:
        List of label values as strings
    """
    data = make_prometheus_request(f"label/{label}/values")
    return data

def setup_environment(url=None, username=None, password=None, token=None, org_id=None):
    """Set up the environment by applying configuration from command line arguments."""
    global config
    
    config = PrometheusConfig(
        url=url or "",
        username=username,
        password=password,
        token=token,
        org_id=org_id
    )
    
    if not config.url:
        print("ERROR: Prometheus URL is not provided")
        print("Please provide it using the --url flag")
        print("Example: --url http://your-prometheus-server:9090")
        return False
    
    print(f"Prometheus configuration:")
    print(f"  Server URL: {config.url}")
    
    if config.username and config.password:
        print("Authentication: Using basic auth")
    elif config.token:
        print("Authentication: Using token")
    else:
        print("Authentication: None (no credentials provided)")
    
    return True

def run_server(url=None, username=None, password=None, token=None, org_id=None, timeout=30, limit=1000):
    """Main entry point for the Prometheus MCP Server"""
    # Setup environment
    if not setup_environment(url, username, password, token, org_id):
        sys.exit(1)
    
    # Update config with timeout and limit values
    global config
    config.timeout = timeout
    config.limit = limit
    
    print(f"Query timeout: {config.timeout}s")
    print(f"Query result limit: {config.limit}")
    print("\nStarting Prometheus MCP Server...")
    print("Running server in standard mode...")
    
    # Run the server with the stdio transport
    mcp.run(transport="stdio")

