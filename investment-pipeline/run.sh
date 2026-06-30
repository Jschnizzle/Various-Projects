#!/bin/bash

# Housing Market Data Downloader - Bash Wrapper
# Makes it easy to run the Python scripts

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
print_header() {
    echo -e "\n${BLUE}======================================================================${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}======================================================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

check_python() {
    if command -v python3 &> /dev/null; then
        PYTHON_CMD=python3
    elif command -v python &> /dev/null; then
        PYTHON_CMD=python
    else
        print_error "Python not found. Please install Python 3.8+"
        exit 1
    fi
    
    # Check version
    VERSION=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
    print_success "Found Python $VERSION"
}

check_dependencies() {
    print_header "Checking Dependencies"
    
    if [ -f "requirements.txt" ]; then
        print_success "requirements.txt found"
    else
        print_error "requirements.txt not found"
        exit 1
    fi
    
    # Check if packages are installed
    if $PYTHON_CMD -c "import pandas" 2>/dev/null; then
        print_success "Dependencies appear to be installed"
    else
        print_warning "Dependencies may not be installed"
        echo "Run: pip install -r requirements.txt"
    fi
}

install_deps() {
    print_header "Installing Dependencies"
    
    echo "This will install all required Python packages..."
    read -p "Continue? (y/n) " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        $PYTHON_CMD -m pip install -r requirements.txt
        print_success "Dependencies installed"
    else
        print_warning "Skipping dependency installation"
    fi
}

run_setup() {
    print_header "Running Setup Wizard"
    $PYTHON_CMD setup.py
}

run_download() {
    print_header "Downloading Housing Market Data"
    $PYTHON_CMD housing_data_downloader.py
}

run_bls() {
    print_header "Downloading BLS Data"
    
    if [ -z "$BLS_API_KEY" ]; then
        print_warning "BLS_API_KEY environment variable not set"
        echo "Get a free API key at: https://www.bls.gov/developers/"
        echo ""
        read -p "Enter your BLS API key (or press Enter to skip): " api_key
        
        if [ ! -z "$api_key" ]; then
            export BLS_API_KEY=$api_key
            $PYTHON_CMD bls_api_downloader.py
        else
            print_warning "Skipping BLS download"
        fi
    else
        print_success "BLS_API_KEY found"
        $PYTHON_CMD bls_api_downloader.py
    fi
}

run_verify() {
    print_header "Verifying Downloaded Data"
    $PYTHON_CMD verify_data.py
}

show_status() {
    print_header "Data Status"
    
    if [ -d "housing_market_data" ]; then
        print_success "Data directory exists"
        
        echo ""
        echo "File counts:"
        for dir in zillow census bls other; do
            if [ -d "housing_market_data/$dir" ]; then
                count=$(find "housing_market_data/$dir" -name "*.csv" -type f | wc -l)
                echo "  $dir: $count files"
            fi
        done
        
        echo ""
        echo "Directory sizes:"
        du -sh housing_market_data/*/ 2>/dev/null || echo "  No subdirectories found"
        
        echo ""
        if [ -f "housing_market_data/download_metadata.json" ]; then
            print_success "Download metadata exists"
        else
            print_warning "No download metadata found"
        fi
        
        if [ -f "housing_market_data/verification_report.json" ]; then
            print_success "Verification report exists"
        else
            print_warning "No verification report found (run verify)"
        fi
    else
        print_error "Data directory not found"
        echo "Run: $0 download"
    fi
}

show_help() {
    cat << EOF
Housing Market Data Analysis - Command Line Tool

USAGE:
    $0 [command]

COMMANDS:
    setup       Run complete setup wizard (recommended for first time)
    install     Install Python dependencies
    download    Download housing market data (Zillow, Census, FHFA, etc.)
    bls         Download BLS employment/wage data (requires API key)
    verify      Verify downloaded data quality
    process     Run data cleaning and feature engineering
    status      Show current data status
    all         Run download + verify
    clean       Remove downloaded data (for fresh start)
    help        Show this help message

EXAMPLES:
    # First time setup
    $0 setup

    # Quick start (download + verify)
    $0 all

    # Individual steps
    $0 install
    $0 download
    $0 verify

    # Check what you have
    $0 status

    # Fresh start
    $0 clean
    $0 download

ENVIRONMENT VARIABLES:
    BLS_API_KEY     Your BLS API key (get free at https://www.bls.gov/developers/)

NOTES:
    - Requires Python 3.8+
    - Total download size: ~500MB-1GB
    - Some data requires manual download (see README.md)

For detailed documentation, see:
    README.md           - Complete guide
    QUICK_REFERENCE.md  - Quick reference

EOF
}

clean_data() {
    print_header "Cleaning Downloaded Data"
    
    if [ -d "housing_market_data" ]; then
        echo "This will DELETE all downloaded data!"
        read -p "Are you sure? (type 'yes' to confirm): " confirm
        
        if [ "$confirm" = "yes" ]; then
            rm -rf housing_market_data
            print_success "Data directory removed"
        else
            print_warning "Cancelled"
        fi
    else
        print_warning "No data directory found"
    fi
}

# Main script
main() {
    echo ""
    echo "╔══════════════════════════════════════════════════════════════════════╗"
    echo "║  Housing Market Investment Analysis - Data Downloader               ║"
    echo "║  CA to TX Migration & Emerging Markets (2024-2025)                  ║"
    echo "╚══════════════════════════════════════════════════════════════════════╝"
    
    # Check for Python
    check_python
    
    # Parse command
    case "${1:-help}" in
        setup)
            run_setup
            ;;
        install)
            install_deps
            ;;
        download)
            check_dependencies
            run_download
            ;;
        bls)
            check_dependencies
            run_bls
            ;;
        verify)
            check_dependencies
            run_verify
            ;;
        all)
            check_dependencies
            run_download
            run_verify
            ;;
        process)
            check_dependencies
            print_header "Running Data Processing Pipeline"
            $PYTHON_CMD data_cleaner.py
            $PYTHON_CMD ca_county_cleaner.py
            $PYTHON_CMD tx_county_cleaner.py
            $PYTHON_CMD feature_engineer.py
            ;;
        status)
            show_status
            ;;
        clean)
            clean_data
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            print_error "Unknown command: $1"
            echo ""
            show_help
            exit 1
            ;;
    esac
    
    echo ""
}

# Run main function
main "$@"
