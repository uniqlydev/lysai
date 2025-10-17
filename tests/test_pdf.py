#!/usr/bin/env python3
"""
Test PDF generation directly
"""
import sys
import os
sys.path.append('/Volumes/DevSSD/github/lysai')

from tools.mcp.tools.pdf_tools import generate_pdf

def test_pdf_generation():
    print("Testing PDF generation...")
    
    # Sample data that matches what the system would generate
    test_data = [
        {"first_name": "GINA", "last_name": "DEGENERES", "film_count": 42},
        {"first_name": "WALTER", "last_name": "TORN", "film_count": 41},
        {"first_name": "MARY", "last_name": "KEITEL", "film_count": 40},
        {"first_name": "MATTHEW", "last_name": "CARREY", "film_count": 39},
        {"first_name": "SANDRA", "last_name": "KILMER", "film_count": 37}
    ]
    
    try:
        result = generate_pdf(
            title="Top Actors by Film Count",
            question="Who are the top 5 actors? Please generate a PDF after",
            insight="The top actors are Gina Degeneres (42 films), Walter Torn (41 films), Mary Keitel (40 films), Matthew Carrey (39 films), and Sandra Kilmer (37 films).",
            rows=test_data,
            chart_x_key="last_name",
            chart_y_key="film_count",
            chart_top_n=5,
            chart_title="Top 5 Actors by Film Count"
        )
        
        print(f"✅ SUCCESS: PDF generated successfully")
        print(f"Result: {result}")
        
        if result.get("ok") and result.get("path"):
            pdf_path = result["path"]
            if os.path.exists(pdf_path):
                print(f"✅ File exists at: {pdf_path}")
                print(f"File size: {os.path.getsize(pdf_path)} bytes")
            else:
                print(f"❌ File does not exist at: {pdf_path}")
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_pdf_generation()