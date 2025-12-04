# Expense Receipt Processor

Automated expense receipt processing using Apple's Vision OCR framework. Extracts date, cost, and details from PDF and image receipts, outputting structured CSV data.

## Features

- **Multi-format support**: Processes PDFs, JPG, and PNG files
- **Apple Vision OCR**: Leverages macOS native OCR for accurate text extraction
- **Smart receipt detection**: Automatically identifies receipt types:
  - Train tickets (Trainline, etc.)
  - Hotels (Premier Inn, Point A, etc.)
  - Parking (airport, station)
  - Food & drinks
  - Tube/Metro (TfL)
  - Flights
- **Intelligent parsing**: Handles corrupted OCR text and poor quality images
- **CSV output**: Structured data with date (DD/MM/YYYY), cost (£), description, and review flags
- **Review flagging**: Automatically marks receipts with missing data for manual verification

## Installation

### Requirements
- macOS (for Apple Vision framework)
- Python 3.8+
- Homebrew (optional, for system Python management)

### Setup

1. Clone the repository:
```bash
git clone git@github.com:DanGahan/expenseProcessor.git
cd expenseProcessor
```

2. Run the setup script:
```bash
./setup.sh
```

This creates a virtual environment and installs dependencies:
- pyobjc-framework-Quartz
- pyobjc-framework-Vision
- python-dateutil

## Usage

### Process Receipts

Activate the virtual environment and run the processor on a directory:

```bash
source venv/bin/activate
./receiptprocess.py "wc 011225"
```

This will:
1. Process all PDF and image files in the directory
2. Skip files with "Pre-Approval" in the name
3. Extract date, cost, and description from each receipt
4. Create `expenses.csv` in the target directory

### CSV Output

The generated CSV contains:
- **Filename**: Source file name
- **Date**: Transaction date (DD/MM/YYYY format)
- **Cost**: Amount in GBP (£)
- **Comment**: Description (e.g., "Train from Cardiff to London", "1 night(s) at Premier Inn")
- **Review**: Flags receipts with missing data (e.g., "REVIEW: missing cost")

### Weekly Preparation

Create a new weekly expense directory:

```bash
./weekprep.sh
```

This automatically:
- Creates directory named `wc DDMMYY` for the coming Monday
- Copies the travel pre-approval form template
- Renames the form with the correct week date

### Debug OCR Output

View raw OCR text from a receipt:

```bash
source venv/bin/activate
python3 debug_pdf.py "path/to/receipt.pdf"
```

## Examples

### Example 1: Train Ticket
**Input**: TrainToLondon.pdf
**Output**:
```csv
TrainToLondon.pdf,14/10/2025,£124.29,Train from Cardiff to London,
```

### Example 2: Hotel Receipt
**Input**: Hotel.jpg (poor quality image)
**Output**:
```csv
Hotel.jpg,03/12/2025,£148.00,1 night(s) at Premier Inn,
```

### Example 3: Parking
**Input**: AirportParking.pdf
**Output**:
```csv
AirportParking.pdf,27/11/2025,£75.00,Parking,
```

### Example 4: Flagged for Review
**Input**: Receipt with corrupted text
**Output**:
```csv
BadReceipt.jpg,,,Unknown expense,REVIEW: missing date, missing cost
```

## File Structure

```
expenseProcessor/
├── receiptprocess.py       # Main receipt processor
├── weekprep.sh            # Weekly directory setup
├── debug_pdf.py           # OCR debugging tool
├── email_receipt_parser.py # Email receipt parser (future)
├── setup.sh               # Virtual environment setup
├── requirements.txt       # Python dependencies
├── README.md             # This file
└── .gitignore            # Git ignore rules
```

## How It Works

1. **Text Extraction**:
   - PDFs: Extracts embedded text, falls back to Vision OCR if corrupted
   - Images: Uses Apple Vision OCR directly

2. **Receipt Type Detection**:
   - Keyword matching (e.g., "Trainline" → train ticket)
   - Pattern recognition (e.g., station names, hotel chains)
   - Fallback scoring system for ambiguous receipts

3. **Data Parsing**:
   - Dates: Multiple format support with normalization to DD/MM/YYYY
   - Costs: Handles corrupted OCR (£4.?0 → £4.70), missing symbols, garbled text
   - Descriptions: Context-aware generation based on receipt type

4. **Error Handling**:
   - Marks receipts with missing critical data
   - Attempts OCR error correction
   - Provides fallback patterns for common corruptions

## Limitations

- Requires macOS (Apple Vision framework dependency)
- Works best with clear, well-lit images
- May struggle with extremely corrupted or handwritten receipts
- Currently optimized for UK receipts (GBP, UK rail, TfL)

## Troubleshooting

**Problem**: No text extracted from image
**Solution**: Check image quality, ensure it's not upside down or too blurry

**Problem**: Wrong receipt type detected
**Solution**: Receipt may have ambiguous keywords, check Review column

**Problem**: Missing cost or date
**Solution**: Look for Review flag, may need manual entry for that receipt

**Problem**: Virtual environment issues
**Solution**: Delete `venv/` folder and re-run `./setup.sh`

## Future Enhancements

- [ ] Email receipt parsing (from .eml files)
- [ ] Bank statement cross-reference
- [ ] Multi-currency support
- [ ] Receipt categorization for tax purposes
- [ ] Export to accounting software formats

## Contributing

This is a personal expense management tool. Feel free to fork and adapt for your own use.

## License

MIT License - Use freely for personal or commercial purposes.

---

**Built with Apple Intelligence** 🍎
*Generated with [Claude Code](https://claude.com/claude-code)*
