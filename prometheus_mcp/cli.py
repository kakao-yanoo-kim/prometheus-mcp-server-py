#!/usr/bin/env python

import sys
import argparse
from prometheus_mcp import run_server

def parse_arguments():
    """Parse command line arguments for the application."""
    parser = argparse.ArgumentParser(description="Prometheus MCP Server")
    parser.add_argument("--url", help="Prometheus server URL (required)")
    parser.add_argument("--username", help="Username for basic authentication")
    parser.add_argument("--password", help="Password for basic authentication")
    parser.add_argument("--token", help="Token for authentication")
    parser.add_argument("--org-id", help="Organization ID for multi-tenancy")
    parser.add_argument("--timeout", type=int, default=30, help="Evaluation timeout in seconds (default: 30)")
    parser.add_argument("--limit", type=int, default=1000, help="Maximum number of returned series (default: 1000)")
    
    return parser.parse_args()

def main():
    """Command line entry point for the Prometheus MCP Server."""
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
    return 0

if __name__ == "__main__":
    sys.exit(main())
