from pdfminer.pdfinterp import PDFResourceManager
from pdfminer.layout import LAParams
from pdfminer.pdfinterp import PDFPageInterpreter
from pdfminer.converter import PDFPageAggregator

def init_interpreter():
    """
    Load pdfminer6 interpreter for layout/content parsing.
    """
    rsrcmgr  = PDFResourceManager()
    laparams = LAParams(char_margin=1)
    
    device = PDFPageAggregator(rsrcmgr, laparams=laparams)
    interpreter = PDFPageInterpreter(rsrcmgr, device)

    return device, interpreter