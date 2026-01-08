"""Quick regression test for other vendor extractors."""

from pathlib import Path
from docling.document_converter import DocumentConverter
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import PdfFormatOption
import sys
import importlib.util

sys.path.insert(0, str(Path(__file__).parent.parent))

# Load extractors using importlib to avoid circular imports
def load_extractor(name):
    spec = importlib.util.spec_from_file_location(
        f"{name}_extractor",
        Path(__file__).parent.parent / "extractors" / f"{name}.py"
    )
    module = importlib.util.module_from_spec(spec)

    # Load base first
    if 'extractors.base' not in sys.modules:
        base_spec = importlib.util.spec_from_file_location(
            "base_extractor",
            Path(__file__).parent.parent / "extractors" / "base.py"
        )
        base_module = importlib.util.module_from_spec(base_spec)
        sys.modules['extractors.base'] = base_module
        base_spec.loader.exec_module(base_module)

    sys.modules[f'extractors.{name}'] = module
    spec.loader.exec_module(module)
    return module


class SimpleProcessor:
    def __init__(self):
        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = True
        self.converter = DocumentConverter(
            format_options={'pdf': PdfFormatOption(pipeline_options=pipeline_options)}
        )
        self.document_cache = {}

    def convert_document(self, pdf_path: str) -> str:
        pdf_path_str = str(Path(pdf_path).resolve())
        if pdf_path_str in self.document_cache:
            return pdf_path_str
        result = self.converter.convert(pdf_path_str)
        self.document_cache[pdf_path_str] = result.document
        return pdf_path_str

    def get_document_markdown(self, doc_key: str, max_size=None) -> str:
        doc = self.document_cache[doc_key]
        markdown = doc.export_to_markdown()
        if max_size and len(markdown) > max_size:
            return markdown[:max_size]
        return markdown


def main():
    processor = SimpleProcessor()

    print('Regression Test: Other Vendors\n')
    print(f'{"Vendor":<20} {"File":<40} {"Conf":<6} {"Status"}')
    print('-' * 80)

    # Test Reflex
    reflex_file = '/Users/dalton/Library/CloudStorage/Dropbox/02_clients/VoChill/[01]-Accounting/AP/Bills/Reflex/Bill_62935_Inv_62935_from_REFLEX_MEDICAL_CORP_1280567_199.pdf'
    try:
        reflex_module = load_extractor('reflex_medical')
        extractor = reflex_module.ReflexMedicalExtractor(processor)
        doc_key = processor.convert_document(reflex_file)
        markdown = processor.get_document_markdown(doc_key)
        invoice = extractor.extract(doc_key, markdown, 'Bill_62935.pdf')
        conf = invoice.extraction_confidence
        status = 'PASS ✓' if conf >= 0.90 else 'DEGRADED ✗'
        print(f'{"Reflex Medical":<20} {"Bill_62935.pdf":<40} {conf:.2f}  {status}')
    except Exception as e:
        print(f'{"Reflex Medical":<20} {"Bill_62935.pdf":<40} {"FAIL":<6} Exception: {str(e)[:30]}')

    # Test OMICO
    omico_file = '/Users/dalton/Library/CloudStorage/Dropbox/02_clients/VoChill/[01]-Accounting/AP/Bills/Omico/Bill_95998_95998.pdf'
    try:
        omico_module = load_extractor('omico')
        extractor = omico_module.OmicoExtractor(processor)
        doc_key = processor.convert_document(omico_file)
        markdown = processor.get_document_markdown(doc_key)
        invoice = extractor.extract(doc_key, markdown, 'Bill_95998.pdf')
        conf = invoice.extraction_confidence
        status = 'PASS ✓' if conf >= 0.80 else 'DEGRADED ✗'
        print(f'{"OMICO":<20} {"Bill_95998.pdf":<40} {conf:.2f}  {status}')
    except Exception as e:
        print(f'{"OMICO":<20} {"Bill_95998.pdf":<40} {"FAIL":<6} Exception: {str(e)[:30]}')

    print('-' * 80)
    print('\nRegression test complete.')


if __name__ == '__main__':
    main()
