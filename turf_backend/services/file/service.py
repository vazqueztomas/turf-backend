from pathlib import Path


class FileService:
    def __init__(self) -> None:
        self.save_dir = Path("files")
        self.save_dir.mkdir(parents=True, exist_ok=True)

    def save_file(self, file_path: Path, content: bytes) -> None:
        with file_path.open("wb") as file_:
            file_.write(content)

    def list_available_files(self, path: Path) -> list[str]:
        pdf_files = list(path.glob("*.pdf"))
        return [file.name for file in pdf_files]

    def retrieve_file(self, path: Path, filename: str) -> bytes | None:
        pdf_file = path / filename
        if not pdf_file.exists():
            return None
        return pdf_file.read_bytes()
