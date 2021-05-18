import pdfgravy

pdf = pdfgravy.PDF('tests/pdfs/apple_65.pdf')
for page in pdf.pages:
    page.extract_tables()