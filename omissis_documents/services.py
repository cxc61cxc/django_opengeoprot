import os
import subprocess
from pathlib import Path

from django.conf import settings
from docx import Document
from docx.oxml.ns import qn


def _placeholder() -> str:
    return getattr(settings, "OMISSIS_PLACEHOLDER", None) or "...omissis..."


def _libreoffice_bin() -> str:
    return (
        getattr(settings, "OMISSIS_LIBREOFFICE_BIN", None)
        or os.environ.get("LIBREOFFICE_BIN")
        or "libreoffice"
    )


def _libreoffice_timeout() -> int:
    return getattr(settings, "OMISSIS_LIBREOFFICE_TIMEOUT", 120) or 120


def ensure_docx(input_path: Path, workdir: Path) -> Path:
    """
    Se il file è già .docx, lo restituisce.
    Altrimenti converte il file in .docx usando LibreOffice headless.
    """
    input_path = Path(input_path)
    workdir = Path(workdir)

    if input_path.suffix.lower() == ".docx":
        return input_path

    # Profilo temporaneo per evitare conflitti tra conversioni concorrenti.
    profile_dir = workdir / "libreoffice_profile"
    profile_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        _libreoffice_bin(),
        f"-env:UserInstallation={profile_dir.as_uri()}",
        "--headless",
        "--norestore",
        "--convert-to",
        "docx",
        "--outdir",
        str(workdir),
        str(input_path),
    ]

    subprocess.run(
        cmd,
        check=True,
        capture_output=True,
        timeout=_libreoffice_timeout(),
    )

    converted = workdir / f"{input_path.stem}.docx"

    if not converted.exists():
        candidates = list(workdir.glob("*.docx"))
        if not candidates:
            raise RuntimeError("Conversione in DOCX non riuscita.")
        converted = candidates[0]

    return converted


def _attr_is_true(element) -> bool:
    """
    Interpreta attributi OOXML tipo:
    <w:strike/>
    <w:strike w:val="true"/>
    <w:strike w:val="1"/>

    Restituisce False se:
    <w:strike w:val="0"/>
    <w:strike w:val="false"/>
    <w:strike w:val="none"/>
    """
    if element is None:
        return False

    val = element.get(qn("w:val"))

    if val is None:
        return True

    return val.strip().lower() not in ("0", "false", "none")


def _direct_strike_state(run):
    """
    Restituisce:
    - True se la run ha barrato diretto attivo
    - False se la run ha barrato diretto disattivato esplicitamente
    - None se non c'è informazione diretta
    """
    try:
        rPr = run._r.rPr
        if rPr is None:
            return None

        has_false = False

        for tag in ("w:strike", "w:dstrike"):
            element = rPr.find(qn(tag))

            if element is None:
                continue

            if _attr_is_true(element):
                return True

            has_false = True

        if has_false:
            return False

    except Exception:
        pass

    return None


def _run_is_strike(run) -> bool:
    """
    Cerca di capire se una run è barrata.

    Controlla:
    1. formattazione diretta XML;
    2. proprietà python-docx;
    3. stile della run, per quanto disponibile.
    """
    direct_state = _direct_strike_state(run)

    if direct_state is not None:
        return direct_state

    try:
        if run.font.strike:
            return True
    except Exception:
        pass

    try:
        if getattr(run.font, "double_strike", False):
            return True
    except Exception:
        pass

    # Controllo dello stile associato alla run.
    # Non copre tutti i casi possibili di ereditarietà,
    # ma aiuta quando il barrato deriva da uno stile.
    try:
        style = getattr(run, "style", None)

        if style is not None and getattr(style, "font", None) is not None:
            if style.font.strike:
                return True

            if getattr(style.font, "double_strike", False):
                return True

    except Exception:
        pass

    return False


def _clear_strike(run) -> None:
    """
    Imposta esplicitamente il barrato a False.

    Questo è importante anche quando il barrato deriva da uno stile:
    la formattazione diretta False dovrebbe prevalere sullo stile.
    """
    try:
        run.font.strike = False
    except Exception:
        pass

    try:
        if hasattr(run.font, "double_strike"):
            run.font.double_strike = False
    except Exception:
        pass


def _process_paragraph(paragraph) -> None:
    """
    Elabora un paragrafo.

    Se trova una sequenza di run barrate consecutive,
    inserisce un solo placeholder.
    """
    group = []
    placeholder = _placeholder()

    def flush_group():
        nonlocal group

        if not group:
            return

        first = next((r for r in group if r.text.strip()), None)

        if first is not None:
            first.text = placeholder
            _clear_strike(first)

        for run in group:
            if run is not first:
                run.text = ""
                _clear_strike(run)

        group = []

    for run in paragraph.runs:
        if _run_is_strike(run):
            group.append(run)
        else:
            flush_group()

    flush_group()


def _process_table(table) -> None:
    for row in table.rows:
        for cell in row.cells:
            _process_container(cell)


def _process_container(container) -> None:
    """
    Elabora paragrafi e tabelle contenuti in un oggetto.
    Funziona per Document, Cell, Header/Footer, ecc.
    """
    for paragraph in getattr(container, "paragraphs", []):
        _process_paragraph(paragraph)

    for table in getattr(container, "tables", []):
        _process_table(table)


def replace_strikethrough_docx(input_docx: Path, output_docx: Path) -> None:
    """
    Apre un file .docx, sostituisce il testo barrato con il placeholder
    e salva un nuovo file.
    """
    input_docx = Path(input_docx)
    output_docx = Path(output_docx)

    doc = Document(str(input_docx))

    # Corpo principale del documento
    _process_container(doc)

    # Intestazioni e piè di pagina
    for section in doc.sections:
        for part_name in (
            "header",
            "footer",
            "first_page_header",
            "first_page_footer",
            "even_page_header",
            "even_page_footer",
        ):
            part = getattr(section, part_name, None)

            if part is not None:
                _process_container(part)

    doc.save(str(output_docx))