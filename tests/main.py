from pdf import PDF

pdf = PDF('tests/out.pdf')

for page in pdf.pages:
    page.extract_tables()