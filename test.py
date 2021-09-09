import pdfgravy

pdf = pdfgravy.Pdf('tests/pdfs/msft.pdf')
for page in pdf.pages:
    page.extract_tables()