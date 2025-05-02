import requests
import argparse
import sys
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from requests.auth import HTTPBasicAuth
from mcp.server.fastmcp import FastMCP

# Initialize MCP server instance
mcp = FastMCP("Prometheus MCP")

@dataclass
class PrometheusConfig:
    url: str
    username: Optional[str] = None
    password: Optional[str] = None
    token: Optional[str] = None
    org_id: Optional[str] = None
    timeout: int = 30
    limit: int = 1000

# Global config variable, to be populated in setup_environment
config: PrometheusConfig

def get_prometheus_auth() -> Union[Dict[str, str], HTTPBasicAuth, None]:
    """
    Determine authentication method based on configuration.
    Returns a dict for headers if using token,
    an HTTPBasicAuth object if using basic auth, or None.
    """
    if config.token:
        return {"Authorization": f"{config.token}"}
    if config.username and config.password:
        return HTTPBasicAuth(config.username, config.password)
    return None


def make_prometheus_request(endpoint: str, params: Dict[str, Any] = None) -> Any:
    """
    Send a GET request to the Prometheus HTTP API endpoint and return the parsed 'data' section.
    Raises ValueError if configuration is missing or if API returns an error status.
    """
    if not config.url:
        raise ValueError("Prometheus URL is not set. Use the --url flag to specify it.")
    url = f"{config.url.rstrip('/')}/api/v1/{endpoint.lstrip('/')}"
    auth = None
    headers: Dict[str, str] = {}

    auth_or_headers = get_prometheus_auth()
    if isinstance(auth_or_headers, dict):
        headers.update(auth_or_headers)
    elif isinstance(auth_or_headers, HTTPBasicAuth):
        auth = auth_or_headers

    if config.org_id:
        headers["X-Scope-OrgID"] = config.org_id

    response = requests.get(url, params=params, auth=auth, headers=headers)
    response.raise_for_status()
    body = response.json()
    if body.get("status") != "success":
        raise ValueError(f"Prometheus API error: {body}")
    return body.get("data")

@mcp.tool
def execute_query(query: str, time: Optional[str] = None, timeout: Optional[int] = None, limit: Optional[int] = None) -> Dict[str, Any]:
    """
    Execute an instant PromQL query.
    Returns the resultType and result array.
    
    Parameters:
    - query: The PromQL query string
    - time: Optional evaluation timestamp
    - timeout: Evaluation timeout in seconds (defaults to 30s if not specified)
    - limit: Maximum number of returned series (defaults to 1000 if not specified)
    """
    params = {"query": query}
    if time:
        params["time"] = time
    if timeout is None:
        timeout = config.timeout
    if limit is None:
        limit = config.limit
    
    params["timeout"] = str(timeout)
    params["limit"] = str(limit)
    
    data = make_prometheus_request("query", params)
    return {"resultType": data.get("resultType"), "result": data.get("result")}

@mcp.tool
def execute_range_query(query: str, start: str, end: str, step: str, timeout: Optional[int] = None, limit: Optional[int] = None) -> Dict[str, Any]:
    """
    Execute a PromQL range query.
    Returns the resultType and result array.
    
    Parameters:
    - query: The PromQL query string
    - start: Start timestamp
    - end: End timestamp
    - step: Query resolution step width
    - timeout: Evaluation timeout in seconds (defaults to 30s if not specified)
    - limit: Maximum number of returned series (defaults to 1000 if not specified)
    """
    params = {"query": query, "start": start, "end": end, "step": step}
    
    if timeout is None:
        timeout = config.timeout
    if limit is None:
        limit = config.limit
    
    params["timeout"] = str(timeout)
    params["limit"] = str(limit)
    
    data = make_prometheus_request("query_range", params)
    return {"resultType": data.get("resultType"), "result": data.get("result")}

@mcp.tool
def get_rules(type: Optional[str] = None) -> Dict[str, Any]:
    """
    Retrieve alerting and recording rules that are currently loaded.
    Returns groups of rules with their current state.
    
    Parameters:
    - type: Optional filter to only return rules of a certain type ('alert' or 'recording')
    """
    params = {}
    if type:
        params["type"] = type
    
    return make_prometheus_request("rules", params)

@mcp.tool
def list_metrics() -> List[str]:
    """
    List all metric names.
    """
    return make_prometheus_request("label/__name__/values")

@mcp.tool
def get_labels() -> List[str]:
    """
    List all available label names.
    """
    return make_prometheus_request("labels")

@mcp.tool
def get_label_values(label: str) -> List[str]:
    """
    Retrieve all values for a given label name.
    """
    return make_prometheus_request(f"label/{label}/values")


def parse_arguments():
    """
    Parse command line arguments for the application.
    """
    parser = argparse.ArgumentParser(description="Prometheus MCP Server")
    parser.add_argument("--url", help="Prometheus server URL", required=True)
    parser.add_argument("--username", help="Username for basic authentication")
    parser.add_argument("--password", help="Password for basic authentication")
    parser.add_argument("--token", help="Token for authentication")
    parser.add_argument("--org-id", help="Organization ID for multi-tenancy")
    parser.add_argument("--timeout", type=int, default=30, help="Evaluation timeout in seconds (default: 30)")
    parser.add_argument("--limit", type=int, default=1000, help="Maximum number of returned series (default: 1000)")
    
    return parser.parse_args()


def setup_environment() -> bool:
    """
    Load command line arguments and populate global config.
    Prints a summary and returns False if required arguments are missing.
    """
    global config
    args = parse_arguments()
    
    config = PrometheusConfig(
        url=args.url,
        username=args.username,
        password=args.password,
        token=args.token,
        org_id=args.org_id,
        timeout=args.timeout,
        limit=args.limit,
    )
    
    if not config.url:
        print("Error: --url must be provided", file=sys.stderr)
        return False
        
    print(f"Prometheus URL: {config.url}")
    if config.username:
        print(f"Basic auth user: {config.username}")
    if config.token:
        print("Using token authentication")
    if config.org_id:
        print(f"Using Org ID: {config.org_id}")
    print(f"Query timeout: {config.timeout}s")
    print(f"Query result limit: {config.limit}")
        
    return True


def run_server(url=None, username=None, password=None, token=None, org_id=None, timeout=30, limit=1000):
    """
    Validate environment and start the MCP server over stdio.
    """
    global config
    
    # Set up config directly from parameters
    config = PrometheusConfig(
        url=url,
        username=username,
        password=password,
        token=token,
        org_id=org_id,
        timeout=timeout,
        limit=limit,
    )
    
    if not config.url:
        print("Error: Prometheus URL is required", file=sys.stderr)
        sys.exit(1)
        
    print(f"Prometheus URL: {config.url}")
    if config.username:
        print(f"Basic auth user: {config.username}")
    if config.token:
        print("Using token authentication")
    if config.org_id:
        print(f"Using Org ID: {config.org_id}")
    print(f"Query timeout: {config.timeout}s")
    print(f"Query result limit: {config.limit}")
    
    # Run the server with stdio transport
    mcp.run(transport="stdio")


if __name__ == "__main__":
    args = parse_arguments()
    
    run_server(
        url=args.url,
        username=args.username,
        password=args.password,
        token=args.token,
        org_id=args.org_id,
        timeout=args.timeout,
        limit=args.limit
    )