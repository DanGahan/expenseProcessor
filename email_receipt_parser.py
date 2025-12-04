#!/usr/bin/env python3
"""
Parse receipts directly from email files (.eml)
More reliable than PDFs for Trainline, hotel bookings, etc.
"""

import email
import re
from email import policy
from datetime import datetime

def parse_trainline_email(email_content):
    """Parse Trainline booking confirmation email"""
    data = {
        'vendor': 'Trainline',
        'type': 'train',
        'date': None,
        'cost': None,
        'route': None
    }

    # Extract total amount
    total_match = re.search(r'Total amount:\s*£([\d.]+)', email_content)
    if total_match:
        data['cost'] = f"£{total_match.group(1)}"

    # Extract journey date
    date_match = re.search(r'(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})', email_content, re.IGNORECASE)
    if date_match:
        try:
            parsed_date = datetime.strptime(date_match.group(1), '%d %B %Y')
            data['date'] = parsed_date.strftime('%d/%m/%Y')
        except:
            pass

    # Extract route (from -> to)
    route_patterns = [
        r'return trip\s+([^(]+?)\s+to\s+([^\n\(]+)',
        r'booking confirmation for\s+([^t]+?)\s+to\s+([^\n\(]+)',
    ]

    for pattern in route_patterns:
        match = re.search(pattern, email_content, re.IGNORECASE)
        if match:
            origin = match.group(1).strip()
            destination = match.group(2).strip()
            data['route'] = f"Train from {origin} to {destination}"
            break

    return data


def parse_hotel_email(email_content):
    """Parse hotel booking confirmation email"""
    data = {
        'vendor': 'Hotel',
        'type': 'hotel',
        'date': None,
        'cost': None,
        'details': None
    }

    # Common hotel booking patterns
    # Booking.com, Hotels.com, direct bookings

    # Extract total/cost
    cost_patterns = [
        r'Total.*?£([\d.]+)',
        r'Amount.*?£([\d.]+)',
        r'Price.*?£([\d.]+)',
    ]

    for pattern in cost_patterns:
        match = re.search(pattern, email_content, re.IGNORECASE)
        if match:
            data['cost'] = f"£{match.group(1)}"
            break

    return data


def parse_eml_file(eml_path):
    """Parse .eml email file"""
    with open(eml_path, 'rb') as f:
        msg = email.message_from_binary_file(f, policy=policy.default)

    # Get email body
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                body += part.get_content()
            elif part.get_content_type() == "text/html":
                # Could parse HTML here if needed
                pass
    else:
        body = msg.get_content()

    # Detect email type and parse accordingly
    subject = msg['subject'] or ""
    sender = msg['from'] or ""

    if 'trainline' in sender.lower() or 'trainline' in subject.lower():
        return parse_trainline_email(body)
    elif 'hotel' in subject.lower() or 'booking' in subject.lower():
        return parse_hotel_email(body)

    return None


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        result = parse_eml_file(sys.argv[1])
        if result:
            print(f"Vendor: {result['vendor']}")
            print(f"Date: {result.get('date', 'N/A')}")
            print(f"Cost: {result.get('cost', 'N/A')}")
            print(f"Details: {result.get('route') or result.get('details', 'N/A')}")
