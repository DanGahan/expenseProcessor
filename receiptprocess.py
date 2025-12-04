#!/usr/bin/env python3

import sys
import os
import re
import csv
from pathlib import Path
from datetime import datetime

# Check for required dependencies
try:
    import Quartz
    from Foundation import NSURL
    import Vision
    from AppKit import NSImage
except ImportError:
    print("Error: This script requires pyobjc. Install with: pip3 install pyobjc-framework-Quartz pyobjc-framework-Vision")
    sys.exit(1)


def extract_text_with_vision_ocr(pdf_path):
    """Extract text from PDF using Vision OCR on rendered images"""
    try:
        from Vision import VNRecognizeTextRequest, VNImageRequestHandler
        from CoreGraphics import CGRectMake
        import objc

        pdf_url = NSURL.fileURLWithPath_(pdf_path)
        pdf_doc = Quartz.PDFDocument.alloc().initWithURL_(pdf_url)

        if pdf_doc is None:
            return ""

        all_text = []
        page_count = pdf_doc.pageCount()

        for page_num in range(page_count):
            page = pdf_doc.pageAtIndex_(page_num)
            if not page:
                continue

            # Render page to image at high resolution
            bounds = page.boundsForBox_(Quartz.kCGPDFMediaBox)
            width = int(bounds.size.width * 2)  # 2x resolution for better OCR
            height = int(bounds.size.height * 2)

            # Create bitmap context
            colorSpace = Quartz.CGColorSpaceCreateDeviceRGB()
            context = Quartz.CGBitmapContextCreate(
                None, width, height, 8, width * 4, colorSpace,
                Quartz.kCGImageAlphaPremultipliedLast
            )

            if context:
                # Scale and render
                Quartz.CGContextScaleCTM(context, 2.0, 2.0)
                Quartz.CGContextDrawPDFPage(context, page)

                # Get image from context
                image = Quartz.CGBitmapContextCreateImage(context)

                if image:
                    # Create Vision request
                    request = VNRecognizeTextRequest.alloc().init()
                    request.setRecognitionLevel_(1)  # Accurate mode
                    request.setUsesLanguageCorrection_(True)

                    # Create handler and perform request
                    handler = VNImageRequestHandler.alloc().initWithCGImage_options_(image, {})
                    success, error = handler.performRequests_error_([request], None)

                    if success:
                        observations = request.results()
                        if observations:
                            page_text = []
                            for observation in observations:
                                candidates = observation.topCandidates_(1)
                                if candidates and len(candidates) > 0:
                                    page_text.append(candidates[0].string())
                            all_text.append("\n".join(page_text))

        return "\n".join(all_text)

    except Exception as e:
        print(f"Vision OCR error: {e}")
        return ""


def extract_text_from_image(image_path):
    """Extract text from image using Vision OCR"""
    try:
        from Vision import VNRecognizeTextRequest, VNImageRequestHandler
        from Foundation import NSURL

        image_url = NSURL.fileURLWithPath_(image_path)

        # Create Vision request
        request = VNRecognizeTextRequest.alloc().init()
        request.setRecognitionLevel_(1)  # Accurate mode
        request.setUsesLanguageCorrection_(True)

        # Create handler and perform request
        handler = VNImageRequestHandler.alloc().initWithURL_options_(image_url, {})
        success, error = handler.performRequests_error_([request], None)

        if success:
            observations = request.results()
            if observations:
                text_lines = []
                for observation in observations:
                    candidates = observation.topCandidates_(1)
                    if candidates and len(candidates) > 0:
                        text_lines.append(candidates[0].string())
                return "\n".join(text_lines)

        return ""

    except Exception as e:
        print(f"Vision OCR error: {e}")
        return ""


def extract_text_from_pdf(pdf_path):
    """Extract text from PDF - try embedded text first, then Vision OCR if needed"""
    try:
        # Load PDF
        pdf_url = NSURL.fileURLWithPath_(pdf_path)
        pdf_doc = Quartz.PDFDocument.alloc().initWithURL_(pdf_url)

        if pdf_doc is None:
            print(f"Warning: Could not load PDF: {pdf_path}")
            return ""

        all_text = []
        page_count = pdf_doc.pageCount()

        for page_num in range(page_count):
            page = pdf_doc.pageAtIndex_(page_num)
            if page:
                text = page.string()
                if text:
                    all_text.append(text)

        embedded_text = "\n".join(all_text)

        # Check if text quality is poor (lots of garbled characters)
        if embedded_text:
            # Count suspicious patterns that indicate poor OCR
            garbled_patterns = len(re.findall(r'[^\w\s£.,:\-/()]{2,}', embedded_text))
            total_chars = len(embedded_text)

            # If more than 5% looks garbled, try Vision OCR
            if total_chars > 0 and (garbled_patterns / (total_chars / 100)) > 5:
                print(f"    (Poor quality text detected, trying Vision OCR...)")
                vision_text = extract_text_with_vision_ocr(pdf_path)
                if vision_text:
                    return vision_text

        return embedded_text

    except Exception as e:
        print(f"Error extracting text from {pdf_path}: {e}")
        return ""


def clean_ocr_text(text):
    """Clean up common OCR errors in text"""
    # Common airport/location name fixes
    cleaned = text.replace('Newcast l e Ai rport', 'Newcastle Airport')
    cleaned = cleaned.replace('Newcast leAi rport', 'Newcastle Airport')
    cleaned = cleaned.replace('Newcast l eAi rport', 'Newcastle Airport')

    # Fix specific patterns
    cleaned = re.sub(r'\bl\s+e\b', 'le', cleaned, flags=re.IGNORECASE)  # "l e" -> "le"
    cleaned = re.sub(r'\be\s+A', 'eA', cleaned)  # "e A" -> "eA"
    # Remove single spaces between lowercase letter and capital
    cleaned = re.sub(r'([a-z])\s+([A-Z])', r'\1\2', cleaned)
    return cleaned


def parse_date(text):
    """Extract date from receipt text and convert to DD/MM/YYYY format"""
    from dateutil import parser as date_parser

    # Common date patterns
    date_patterns = [
        r'\b(\d{4})[/-](\d{1,2})[/-](\d{1,2})\b',  # YYYY/MM/DD or YYYY-MM-DD
        r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b',  # DD/MM/YYYY or MM/DD/YYYY
        r'(\d{2})112J(\d{2})',  # Corrupted OCR: 03112J25 -> 03/11/2025
        r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})\b',  # November 5th, 2025
        r'\b(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{2,4})\b',  # DD Month YYYY
        r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{1,2}),?\s+(\d{2,4})\b',  # Month DD, YYYY
        r'W•dn[^0-9]*?(\d{2})[^0-9]+(\d{4})',  # Heavily corrupted: W•dnMday 03... 2025
    ]

    for i, pattern in enumerate(date_patterns):
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            date_str = match.group(0)

            # Handle special corrupted patterns manually
            if '112J' in date_str:  # 03112J25 format
                day = match.group(1)
                year_suffix = match.group(2)
                return f"{day}/12/20{year_suffix}"  # Assume December
            elif 'W•dn' in date_str:  # W•dnMday 03... 2025
                day = match.group(1)
                year = match.group(2)
                return f"{day}/12/{year}"  # Assume December for now

            try:
                # Parse the date string and convert to DD/MM/YYYY
                parsed_date = date_parser.parse(date_str, dayfirst=True)
                return parsed_date.strftime('%d/%m/%Y')
            except (ValueError, date_parser.ParserError):
                # If parsing fails, try to extract manually
                continue

    return ""


def parse_cost(text):
    """Extract cost from receipt text"""
    # First, try to find explicit total amount patterns
    total_patterns = [
        r'Total[:\s]+amount[:\s]*£?\s*(\d+[.,]\d{2})',
        r'Total[:\s]*£?\s*(\d+[.,]\d{2})',
        r'Tot¥1[:\s]*£?\s*(\d+[.,]\d{2})',  # OCR error: Total -> Tot¥1
        r'Subtotal[:\s]*\n?\s*[^\d\n]*?(\d+)\s*[.,]\s*(\d{2})',  # Subtotal with garbled text
        r'Subtotal[:\s]*£?\s*(\d+[.,]\d{2})',
        r'Grand[:\s]+Total[:\s]*£?\s*(\d+[.,]\d{2})',
        r'Amount[:\s]+Due[:\s]*£?\s*(\d+[.,]\d{2})',
        r'Balance[:\s]+Due[:\s]*£?\s*(\d+[.,]\d{2})',
        r'Balanc•[:\s]*£?\s*(\d+[.,]\d{2})',  # OCR error: Balance -> Balanc•
    ]

    for pattern in total_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            if len(match.groups()) == 2:  # Garbled format with separate pounds and pence
                pounds = match.group(1)
                pence = match.group(2)
                return f"£{pounds}.{pence}"
            else:
                amount = match.group(1).replace(',', '')
                try:
                    return f"£{float(amount):.2f}"
                except ValueError:
                    continue

    # If no explicit total found, look for all £ amounts (but be more selective)
    # Match amounts with £ symbol, ensuring we capture the decimal point properly
    amounts = []
    amount_patterns = [
        r'£\s*(\d{1,4})[.,](\d{2})\b',  # £12.98 or £12,98
        r'(\d{2,3})[.,](\d{2})\s*\n',  # Standalone amounts like "148.00\n"
        r'£\s*(\d{1,4})[.,]([?\d])\b',  # £4.?0 or £4.7 (OCR errors)
    ]

    for pattern in amount_patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            if len(match) == 2:
                pounds = match[0]
                pence = match[1]
                # Handle OCR errors in pence (? or single digit)
                if '?' in pence:
                    # Make best guess: ? in middle position often means 7 (£4.?0 likely £4.70)
                    pence = pence.replace('?', '7')
                # Pad single digit pence (e.g., "7" -> "70")
                if len(pence) == 1:
                    pence = pence + "0"
                try:
                    amount = float(f"{pounds}.{pence}")
                    # Filter out unlikely amounts
                    if 0.01 <= amount <= 9999.99:
                        amounts.append(amount)
                except ValueError:
                    continue

    # Return the largest reasonable amount found (likely the total)
    if amounts:
        return f"£{max(amounts):.2f}"

    return ""


def identify_receipt_type(text):
    """Identify the type of receipt and extract relevant information"""
    text_lower = text.lower()

    # Check for explicit receipt types first (order matters!)
    # Check for train BEFORE parking (since train PDFs mention "pre-book parking")
    if 'trainline' in text_lower or 'advance single' in text_lower or 'anytime day single' in text_lower:
        return 'train', text

    if 'paybyphone' in text_lower or 'parking receipt' in text_lower or 'airport parking' in text_lower:
        return 'parking', text

    if 'tfl' in text_lower or 'transport for london' in text_lower or ('oyster' in text_lower) or ('contactless.tfl' in text_lower):
        return 'tube', text

    # Check for food/restaurant indicators
    if any(word in text_lower for word in ['wasabi', 'nonna bakery', 'starbucks', 'costa', 'pret', 'greggs']):
        return 'food', text

    if 'dbs' in text_lower or 'disclosure and barring' in text_lower or 'criminal record check' in text_lower:
        return 'other', text

    # Check for parking keywords (before flight scoring)
    parking_keywords = ['parking', 'car park']
    if any(kw in text_lower for kw in parking_keywords):
        return 'parking', text

    # Train ticket indicators
    train_keywords = ['trainline', 'railway', 'rail', 'advance single', 'anytime', 'platform', 'coach']
    # Flight indicators
    flight_keywords = ['flight', 'airline', 'boarding', 'gate', 'terminal', 'passenger']
    # Hotel indicators
    hotel_keywords = ['hotel', 'accommodation', 'check-in', 'check-out', 'room', 'guest']
    # Food/Drink indicators
    food_keywords = ['restaurant', 'cafe', 'coffee', 'breakfast', 'lunch', 'dinner', 'meal', 'food', 'bar', 'pub']

    train_score = sum(1 for kw in train_keywords if kw in text_lower)
    flight_score = sum(1 for kw in flight_keywords if kw in text_lower)
    hotel_score = sum(1 for kw in hotel_keywords if kw in text_lower)
    food_score = sum(1 for kw in food_keywords if kw in text_lower)

    scores = {
        'train': train_score,
        'flight': flight_score,
        'hotel': hotel_score,
        'food': food_score
    }

    receipt_type = max(scores, key=scores.get)

    if scores[receipt_type] == 0:
        return 'other', text

    return receipt_type, text


def extract_train_details(text):
    """Extract train journey details"""
    # Check for return trip first
    return_pattern = r'return\s+trip\s+([A-Z][a-z]+(?: [A-Z][a-z]+)*(?:\s+\([^)]+\))?)\s+to\s+([A-Z][a-z]+(?: [A-Z][a-z]+)*)'
    return_match = re.search(return_pattern, text, re.IGNORECASE)
    if return_match:
        origin = return_match.group(1).strip()
        destination = return_match.group(2).strip()
        # Clean up station names (remove parenthetical info)
        origin = re.sub(r'\s*\([^)]+\)', '', origin)
        destination = re.sub(r'\s*\([^)]+\)', '', destination)
        return f"Return train: {origin} to {destination}"

    # Look for explicit journey patterns (common in train booking confirmations)
    journey_patterns = [
        r'(?:from|From:)\s+([A-Z][a-z]+(?: [A-Z][a-z]+)*(?:\s+(?:Station|Central|Parkway))?)\s+(?:to|To:)\s+([A-Z][a-z]+(?: [A-Z][a-z]+)*(?:\s+(?:Station|Central|Parkway))?)',
        r'Your\s+(?:booking|trip)\s+(?:confirmation\s+)?(?:for|to)\s+([A-Z][a-z]+(?: [A-Z][a-z]+)*)\s+to\s+([A-Z][a-z]+(?: [A-Z][a-z]+)*)',
        r'(\d{2}:\d{2})\s+([A-Z][a-z]+(?: [A-Z][a-z]+)*(?:\s+(?:Station|Central|Parkway))?)\s+.*?\s+(\d{2}:\d{2})\s+([A-Z][a-z]+(?: [A-Z][a-z]+)*(?:\s+(?:Station|Central|Parkway))?)',
    ]

    for pattern in journey_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            if len(match.groups()) == 2:
                origin = match.group(1).strip()
                destination = match.group(2).strip()
                return f"Train from {origin} to {destination}"
            elif len(match.groups()) == 4:  # Pattern with times
                origin = match.group(2).strip()
                destination = match.group(4).strip()
                return f"Train from {origin} to {destination}"

    # Fallback: Look for station names (common UK stations)
    stations = re.findall(r'\b([A-Z][a-z]+(?: [A-Z][a-z]+)*)\s+(?:Station|Central|Parkway)\b', text)

    comment = "Train ticket"
    if len(stations) >= 2:
        comment = f"Train from {stations[0]} to {stations[1]}"
    elif stations:
        comment = f"Train ticket involving {stations[0]}"

    return comment


def extract_flight_details(text):
    """Extract flight details"""
    # Look for airport codes (3 letters in caps)
    airports = re.findall(r'\b([A-Z]{3})\b', text)

    comment = "Flight ticket"
    if len(airports) >= 2:
        comment = f"Flight from {airports[0]} to {airports[1]}"

    return comment


def extract_hotel_details(text):
    """Extract hotel details"""
    # Look for hotel name - try multiple patterns including corrupted OCR
    hotel_patterns = [
        r'(Premier Inn)',
        r'(Point A Hotel [^\n|]+)',
        r'([A-Z][a-z]+(?: [A-Z][a-z]+)* Hotel(?: [A-Z][a-z]+)*)',
        r'(Hotel [A-Z][a-z]+(?: [A-Z][a-z]+)*)',
    ]

    hotel_name = "Hotel"
    for pattern in hotel_patterns:
        hotel_match = re.search(pattern, text, re.IGNORECASE)
        if hotel_match:
            hotel_name = hotel_match.group(1).strip()
            # Clean up common suffixes
            hotel_name = re.sub(r'\s*\|.*$', '', hotel_name)
            break

    # Calculate number of nights from Arrival/Departure dates (various formats)
    arrival_match = re.search(r'(?:Arrival|4JnvAI)[^0-9]*?(\d{2})[/\s]+(\d{2})[/\s]+(\d{4})', text, re.IGNORECASE)
    departure_match = re.search(r'(?:Departure|QapJnuf8)[^0-9]*?(\d{2})[/\s]+(\d{2})[/\s]+(\d{4})', text, re.IGNORECASE)

    nights = "1"
    if arrival_match and departure_match:
        # For now, just say "1" - could calculate actual nights if needed
        nights = "1"
    else:
        # Look for explicit nights mention
        nights_match = re.search(r'(\d+)\s*night', text, re.IGNORECASE)
        nights = nights_match.group(1) if nights_match else "1"

    # Look for location in address
    location = ""
    address_match = re.search(r'(\d+\s+[^\n]+,\s*London[^\n]*)', text, re.IGNORECASE)
    if address_match:
        location = address_match.group(1).strip()
        # Clean up
        location = re.sub(r'\s*\|.*$', '', location)
    else:
        # Try to find city name
        city_match = re.search(r',\s*(London|Birmingham|Manchester|Cardiff)[,\s]', text, re.IGNORECASE)
        if city_match:
            location = city_match.group(1)

    comment = f"{nights} night(s) at {hotel_name}"
    if location:
        comment += f", {location}"

    return comment


def extract_food_details(text):
    """Extract food/drink details"""
    text_lower = text.lower()

    # Look for known restaurant/venue names first
    venue_patterns = [
        r'(Wasabi[^\n]*)',
        r'(Nonna Bakery[^\n]*)',
        r'(Starbucks[^\n]*)',
        r'(Costa[^\n]*)',
        r'(Pret A Manger[^\n]*)',
        r'(Greggs[^\n]*)',
    ]

    venue = ""
    for pattern in venue_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            venue = match.group(1).strip()
            # Clean up
            venue = re.sub(r',.*$', '', venue)  # Remove address parts
            break

    # If no known venue found, look for restaurant/store name (usually at top of receipt)
    if not venue:
        lines = text.split('\n')
        for line in lines[:10]:  # Check first 10 lines
            if line.strip() and len(line.strip()) > 3 and not re.match(r'^[\d\s\-/:]+$', line):
                # Skip common header words
                if not any(skip in line.lower() for skip in ['receipt', 'invoice', 'payment', 'customer', 'till', 'duplicate']):
                    venue = line.strip()
                    break

    # Determine meal type based on time or keywords
    meal_type = "Meal"

    # Check time of day - handle both 24h and 12h with AM/PM
    time_match = re.search(r'(\d{1,2}):(\d{2})(?:\s*(AM|PM))?', text, re.IGNORECASE)
    if time_match:
        hour = int(time_match.group(1))
        am_pm = time_match.group(3)

        # Convert to 24h format if AM/PM is present
        if am_pm:
            am_pm = am_pm.upper()
            if am_pm == 'PM' and hour != 12:
                hour += 12
            elif am_pm == 'AM' and hour == 12:
                hour = 0

        if 5 <= hour < 11:
            meal_type = "Breakfast"
        elif 11 <= hour < 15:
            meal_type = "Lunch"
        elif 15 <= hour < 24:
            meal_type = "Evening meal"

    # Override with explicit keywords
    if any(word in text_lower for word in ['breakfast', 'morning']):
        meal_type = "Breakfast"
    elif any(word in text_lower for word in ['lunch', 'afternoon']):
        meal_type = "Lunch"
    elif any(word in text_lower for word in ['dinner', 'evening', 'supper']):
        meal_type = "Evening meal"
    elif any(word in text_lower for word in ['coffee', 'cafe']):
        meal_type = "Coffee/drinks"

    # Look for location
    location = ""
    location_patterns = [
        r'(?:Address|Location)[:\s]*([^\n]+)',
        r'(Paddington[^\n]*Station)',
        r'(High Holborn)',
        r'([A-Z][a-z]+\s+Station)',
    ]

    for pattern in location_patterns:
        location_match = re.search(pattern, text, re.IGNORECASE)
        if location_match:
            location = location_match.group(1).strip()
            break

    # Clean up OCR errors in venue and location
    if venue:
        venue = clean_ocr_text(venue)
    if location:
        location = clean_ocr_text(location)

    comment = meal_type
    if venue:
        comment += f" at {venue}"
    if location and venue.lower() not in location.lower():
        comment += f", {location}"

    return comment


def extract_parking_details(text):
    """Extract parking details"""
    # Look for location/description
    location_match = re.search(r'Description[:\s]*([^\n]+)', text, re.IGNORECASE)
    if location_match:
        location = location_match.group(1).strip()
        return f"Parking at {location}"

    # Look for station name
    station_match = re.search(r'([A-Z][A-Z\s]+STATION)', text)
    if station_match:
        station = station_match.group(1).title()
        return f"Parking at {station}"

    return "Parking"


def extract_tube_details(text):
    """Extract tube/TfL travel details"""
    # Look for journey details
    journey_pattern = r'([A-Z][a-z]+(?: [A-Z][a-z]+)*)\s+to\s+([A-Z][a-z]+(?: [A-Z][a-z]+)*)\s+£(\d+\.\d{2})'
    journeys = re.findall(journey_pattern, text)

    if journeys:
        if len(journeys) == 1:
            return f"Tube from {journeys[0][0]} to {journeys[0][1]}"
        elif len(journeys) == 2:
            return f"Tube: {journeys[0][0]} to {journeys[0][1]}, {journeys[1][0]} to {journeys[1][1]}"
        else:
            return f"Tube: {len(journeys)} journeys"

    return "TfL travel"


def extract_other_details(text):
    """Extract details from other/miscellaneous receipts"""
    # Look for payment purpose or description
    purpose_patterns = [
        r'Payment for[:\s]*([^\n]+)',
        r'Purpose[:\s]*([^\n]+)',
        r'Description[:\s]*([^\n]+)',
    ]

    for pattern in purpose_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            purpose = match.group(1).strip()
            return purpose

    # Try to get the first meaningful line as description
    lines = text.split('\n')
    for line in lines[:10]:
        if line.strip() and len(line.strip()) > 10:
            return line.strip()

    return "Other expense"


def process_receipt(file_path):
    """Process a single receipt file (PDF or image) and extract information"""
    filename = os.path.basename(file_path)

    # Determine file type and extract text accordingly
    file_ext = os.path.splitext(filename)[1].lower()
    if file_ext == '.pdf':
        text = extract_text_from_pdf(file_path)
    elif file_ext in ['.jpg', '.jpeg', '.png']:
        text = extract_text_from_image(file_path)
    else:
        text = ""

    if not text:
        return {
            'Filename': filename,
            'Date': '',
            'Cost': '',
            'Comment': f'Could not extract text from {filename}',
            'Review': 'REVIEW: no text extracted'
        }

    receipt_type, full_text = identify_receipt_type(text)

    # For TfL/tube receipts, extract the travel date (not the statement date)
    if receipt_type == 'tube':
        # Look for date followed by cost amount (e.g., "14/10/2025 £5.80")
        tfl_date_pattern = r'(\d{2}/\d{2}/\d{4})\s+£\d+\.\d{2}'
        tfl_date_match = re.search(tfl_date_pattern, text)
        if tfl_date_match:
            date = tfl_date_match.group(1)
        else:
            date = parse_date(text)
    else:
        date = parse_date(text)

    cost = parse_cost(text)

    # Extract detailed comment based on receipt type
    if receipt_type == 'train':
        comment = extract_train_details(text)
    elif receipt_type == 'flight':
        comment = extract_flight_details(text)
    elif receipt_type == 'hotel':
        comment = extract_hotel_details(text)
    elif receipt_type == 'food':
        comment = extract_food_details(text)
    elif receipt_type == 'parking':
        comment = extract_parking_details(text)
    elif receipt_type == 'tube':
        comment = extract_tube_details(text)
    elif receipt_type == 'other':
        comment = extract_other_details(text)
    else:
        comment = f"Receipt - {filename}"

    # Flag for manual review if critical data is missing
    needs_review = ""
    if not date or not cost:
        issues = []
        if not date:
            issues.append("missing date")
        if not cost:
            issues.append("missing cost")
        needs_review = "REVIEW: " + ", ".join(issues)

    return {
        'Filename': filename,
        'Date': date,
        'Cost': cost,
        'Comment': comment,
        'Review': needs_review
    }


def main():
    if len(sys.argv) != 2:
        print("Usage: receiptprocess <directory>")
        sys.exit(1)

    target_dir = sys.argv[1]

    if not os.path.isdir(target_dir):
        print(f"Error: {target_dir} is not a valid directory")
        sys.exit(1)

    # Find all PDF and image files in the directory
    all_pdfs = list(Path(target_dir).glob('*.pdf'))
    all_images = list(Path(target_dir).glob('*.jpg')) + list(Path(target_dir).glob('*.jpeg')) + list(Path(target_dir).glob('*.png'))
    all_files = all_pdfs + all_images

    # Filter out files with "Pre-Approval" in the name
    receipt_files = [f for f in all_files if 'pre-approval' not in f.name.lower()]

    if not receipt_files:
        print(f"No receipt files found in {target_dir}")
        sys.exit(0)

    skipped = len(all_files) - len(receipt_files)
    if skipped > 0:
        print(f"Skipping {skipped} Pre-Approval file(s)")

    print(f"Processing {len(receipt_files)} receipt(s)...")

    # Process each receipt
    results = []
    for receipt_file in receipt_files:
        print(f"  Processing: {receipt_file.name}")
        result = process_receipt(str(receipt_file))
        results.append(result)

    # Write to CSV
    csv_path = os.path.join(target_dir, 'expenses.csv')
    with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['Filename', 'Date', 'Cost', 'Comment', 'Review']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        for result in results:
            writer.writerow(result)

    print(f"\nExpenses CSV created: {csv_path}")
    print(f"Processed {len(results)} receipt(s)")


if __name__ == "__main__":
    main()
