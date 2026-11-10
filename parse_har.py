#!/usr/bin/env python3
"""
parse_har.py — Extract and categorize unique API endpoints from a .har file.
"""

import sys
import json
import argparse
from urllib.parse import urlparse, parse_qs
from pathlib import Path
from collections import defaultdict

STATIC_EXTENSIONS = {
    ".css", ".js", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp",
    ".ico", ".woff", ".woff2", ".ttf", ".eot", ".otf", ".map", ".mp4",
    ".mp3", ".webm", ".avi", ".pdf"
}

IGNORE_DOMAINS = {
    "google-analytics.com", "googletagmanager.com", "analytics.",
    "sentry.io", "hotjar.com", "facebook.com", "clarity.ms", "doubleclick.net"
}

CATEGORIES = {
    "AUTH": ["auth", "login", "otp", "verify", "token", "refresh", "session", "logout", "me"],
    "PROFILE": ["profile", "user", "account", "address", "addresses"],
    "CATALOG": ["catalog", "search", "product", "products", "item", "category", "categories"],
    "CART": ["cart", "basket", "bag"],
    "CHECKOUT": ["checkout", "slot", "slots", "coupon", "voucher", "delivery"],
    "ORDERS": ["order", "orders", "payment", "upi", "track", "tracking"]
}

def categorize_url(path: str) -> str:
    path_lower = path.lower()
    for category, keywords in CATEGORIES.items():
        if any(k in path_lower for k in keywords):
            return category
    return "OTHER"

def is_static_or_tracking(url: str, mime_type: str = "") -> bool:
    parsed = urlparse(url)
    path_lower = parsed.path.lower()

    if any(path_lower.endswith(ext) for ext in STATIC_EXTENSIONS):
        return True

    domain_lower = parsed.netloc.lower()
    if any(tracker in domain_lower for tracker in IGNORE_DOMAINS):
        return True

    if mime_type:
        static_mimes = ["image/", "font/", "text/css", "javascript"]
        if any(sm in mime_type.lower() for sm in static_mimes):
            return True

    return False

def parse_har(har_path: str, domain_filter: str = None, output_file: str = "endpoints_summary.json"):
    path = Path(har_path)
    if not path.is_file():
        print(f"[!] Error: File '{har_path}' not found.")
        sys.exit(1)

    print(f"[*] Loading HAR file: {har_path}...")
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"[!] Invalid JSON format: {e}")
            sys.exit(1)

    entries = data.get("log", {}).get("entries", [])
    print(f"[*] Total network entries found: {len(entries)}")

    unique_endpoints = {}

    for entry in entries:
        req = entry.get("request", {})
        resp = entry.get("response", {})
        
        url = req.get("url", "")
        method = req.get("method", "GET").upper()
        
        resp_mime = resp.get("content", {}).get("mimeType", "")
        if is_static_or_tracking(url, resp_mime):
            continue

        parsed = urlparse(url)
        if domain_filter and domain_filter.lower() not in parsed.netloc.lower():
            continue

        endpoint_key = f"{method} {parsed.netloc}{parsed.path}"

        if endpoint_key in unique_endpoints:
            continue

        extracted_headers = {}
        for h in req.get("headers", []):
            name = h.get("name", "")
            lower_name = name.lower()
            if (
                lower_name.startswith("x-")
                or lower_name in {"authorization", "cookie", "content-type", "accept", "user-agent", "origin", "referer"}
            ):
                extracted_headers[name] = h.get("value", "")

        query_params = {q.get("name"): q.get("value") for q in req.get("queryString", [])}

        post_data = req.get("postData", {})
        body = None
        if post_data:
            text = post_data.get("text", "")
            try:
                body = json.loads(text) if text else None
            except json.JSONDecodeError:
                body = text

        # Response sample
        resp_content = resp.get("content", {}).get("text", "")
        resp_sample = None
        if resp_content:
            try:
                resp_sample = json.loads(resp_content)
            except Exception:
                resp_sample = resp_content[:200]

        category = categorize_url(parsed.path)

        unique_endpoints[endpoint_key] = {
            "category": category,
            "method": method,
            "base_url": f"{parsed.scheme}://{parsed.netloc}",
            "path": parsed.path,
            "query_params": query_params,
            "headers": extracted_headers,
            "payload": body,
            "sample_response_status": resp.get("status"),
            "sample_response_body": resp_sample
        }

    grouped = defaultdict(list)
    for ep, details in unique_endpoints.items():
        grouped[details["category"]].append(details)

    print("\n" + "=" * 60)
    print("EXTRACTED API ENDPOINTS BREAKDOWN")
    print("=" * 60)

    for cat in ["AUTH", "PROFILE", "CATALOG", "CART", "CHECKOUT", "ORDERS", "OTHER"]:
        items = grouped.get(cat, [])
        if not items:
            continue
        print(f"\n[{cat}] ({len(items)} endpoint(s)):")
        for item in items:
            print(f"  • {item['method']:<6} {item['base_url']}{item['path']} (Status: {item['sample_response_status']})")
            if item["query_params"]:
                print(f"      Params: {list(item['query_params'].keys())}")
            if item["payload"]:
                if isinstance(item["payload"], dict):
                    print(f"      Payload Keys: {list(item['payload'].keys())}")
                else:
                    print(f"      Payload Preview: {str(item['payload'])[:60]}")

    with open(output_file, "w", encoding="utf-8") as out:
        json.dump(grouped, out, indent=2)

    print(f"\n[+] Detailed endpoint definitions saved to: {output_file}")
    print(f"[+] Total unique API endpoints identified: {len(unique_endpoints)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parse HAR file for API endpoints")
    parser.add_argument("har_file", help="Path to the .har file")
    parser.add_argument("--domain", help="Optional domain filter", default=None)
    parser.add_argument("--out", help="Output JSON path", default="endpoints_summary.json")
    args = parser.parse_args()

    parse_har(args.har_file, args.domain, args.out)
