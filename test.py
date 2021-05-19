import pdfgravy

pdf = pdfgravy.PDF('tests/pdfs/FB_2.pdf')
for page in pdf.pages:
    page.extract_tables()