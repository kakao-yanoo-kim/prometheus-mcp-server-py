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
async def execute_query(query: str, time: Optional[str] = None) -> Dict[str, Any]:
    """Execute an instant query against Prometheus.
    
    Args:
        query: PromQL query string
        time: Optional RFC3339 or Unix timestamp (default: current time)
        
    Returns:
        Query result with type (vector, matrix, scalar, string) and values
    """
    params = {"query": query}
    if time:
        params["time"] = time
    
    data = make_prometheus_request("query", params=params)
    return {
        "resultType": data["resultType"],
        "result": data["result"]
    }

@mcp.tool(description="Execute a PromQL range query with start time, end time, and step interval")
async def execute_range_query(query: str, start: str, end: str, step: str) -> Dict[str, Any]:
    """Execute a range query against Prometheus.
    
    Args:
        query: PromQL query string
        start: Start time as RFC3339 or Unix timestamp
        end: End time as RFC3339 or Unix timestamp
        step: Query resolution step width (e.g., '15s', '1m', '1h')
        
    Returns:
        Range query result with type (usually matrix) and values over time
    """
    params = {
        "query": query,
        "start": start,
        "end": end,
        "step": step
    }
    
    data = make_prometheus_request("query_range", params=params)
    return {
        "resultType": data["resultType"],
        "result": data["result"]
    }

@mcp.tool(description="List all available metrics in Prometheus")
async def list_metrics() -> List[str]:
    """Retrieve a list of all metric names available in Prometheus.
    
    Returns:
        List of metric names as strings
    """
    data = make_prometheus_request("label/__name__/values")
    return data

@mcp.tool(description="Get metadata for a specific metric")
async def get_metric_metadata(metric: str) -> List[Dict[str, Any]]:
    """Get metadata about a specific metric.
    
    Args:
        metric: The name of the metric to retrieve metadata for
        
    Returns:
        List of metadata entries for the metric
    """
    params = {"metric": metric}
    data = make_prometheus_request("metadata", params=params)
    return data["metadata"]

@mcp.tool(description="Get information about all scrape targets")
async def get_targets() -> Dict[str, List[Dict[str, Any]]]:
    """Get information about all Prometheus scrape targets.
    
    Returns:
        Dictionary with active and dropped targets information
    """
    data = make_prometheus_request("targets")
    return {
        "activeTargets": data["activeTargets"],
        "droppedTargets": data["droppedTargets"]
    }

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

def run_server(url=None, username=None, password=None, token=None, org_id=None):
    """Main entry point for the Prometheus MCP Server"""
    # Setup environment
    if not setup_environment(url, username, password, token, org_id):
        sys.exit(1)
    
    print("\nStarting Prometheus MCP Server...")
    print("Running server in standard mode...")
    
    # Run the server with the stdio transport
    mcp.run(transport="stdio")

