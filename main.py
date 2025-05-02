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
def execute_query(query: str, time: Optional[str] = None) -> Dict[str, Any]:
    """
    Execute an instant PromQL query.
    Returns the resultType and result array.
    """
    params = {"query": query}
    if time:
        params["time"] = time
    data = make_prometheus_request("query", params)
    return {"resultType": data.get("resultType"), "result": data.get("result")}

@mcp.tool
def execute_range_query(query: str, start: str, end: str, step: str) -> Dict[str, Any]:
    """
    Execute a PromQL range query.
    Returns the resultType and result array.
    """
    params = {"query": query, "start": start, "end": end, "step": step}
    data = make_prometheus_request("query_range", params)
    return {"resultType": data.get("resultType"), "result": data.get("result")}

@mcp.tool
def list_metrics() -> List[str]:
    """
    List all metric names.
    """
    return make_prometheus_request("label/__name__/values")

@mcp.tool
def get_metric_metadata(metric: str) -> List[Dict[str, Any]]:
    """
    Retrieve metadata for a given metric name.
    """
    return make_prometheus_request("metadata", {"metric": metric})

@mcp.tool
def get_targets() -> Dict[str, List[Dict[str, Any]]]:
    """
    Retrieve active and dropped scrape targets.
    """
    data = make_prometheus_request("targets")
    return {"active": data.get("activeTargets", []), "dropped": data.get("droppedTargets", [])}


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
        
    return True


def run_server(url=None, username=None, password=None, token=None, org_id=None):
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
    
    # Run the server with stdio transport
    mcp.run(transport="stdio")


if __name__ == "__main__":
    args = parse_arguments()
    
    run_server(
        url=args.url,
        username=args.username,
        password=args.password,
        token=args.token,
        org_id=args.org_id
    )