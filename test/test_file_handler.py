import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from document_processor.file_handler import DocumentProcessor


class DocumentProcessorTest(unittest.TestCase):
    def test_processes_plain_text(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "notes.txt"
            path.write_text("DocChat accepts plain text documents.")

            chunks = DocumentProcessor()._process_file(SimpleNamespace(name=str(path)))

        self.assertEqual(chunks[0].page_content, "DocChat accepts plain text documents.")


if __name__ == "__main__":
    unittest.main()
