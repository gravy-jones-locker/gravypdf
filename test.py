import pdfgravy

pdf = pdfgravy.PDF('tests/pdfs/msft.pdf')
for page in pdf.pages:
    page.extract_tables()