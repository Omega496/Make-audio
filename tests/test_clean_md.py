import io
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

# Add src to path
src_dir = Path(__file__).resolve().parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from pdf.clean_md import main, collect_files, resolve_output_path


def test_default_output_naming():
    """Verify that clean_md input.md creates input_cleaned.md in the same directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        input_file = Path(tmpdir) / "notes.md"
        input_file.write_text("# Chapter 1\n\nThis is a simple markdown file.", encoding="utf-8")

        main([str(input_file)])

        expected_cleaned = Path(tmpdir) / "notes_cleaned.md"
        assert expected_cleaned.exists(), "Default cleaned file notes_cleaned.md was not created!"
        content = expected_cleaned.read_text(encoding="utf-8")
        assert "Chapter 1." in content
        assert "This is a simple markdown file." in content
    print("✓ test_default_output_naming passed")


def test_latex_equations_cleaning():
    """Verify that LaTeX display equations are removed by default and inline math is converted to spoken English."""
    with tempfile.TemporaryDirectory() as tmpdir:
        input_file = Path(tmpdir) / "math_paper.md"
        input_file.write_text(
            "# Physics Notes\n\n"
            "Einstein showed that $E = mc^2$ is fundamental.\n\n"
            "The energy integral is defined as:\n"
            "$$\n"
            "\\int_{0}^{\\infty} e^{-x} dx\n"
            "$$\n\n"
            "Furthermore, $\\alpha \\le \\beta$ holds.\n",
            encoding="utf-8",
        )

        # Default run: display equations removed, inline math spoken
        main([str(input_file)])
        cleaned = (Path(tmpdir) / "math_paper_cleaned.md").read_text(encoding="utf-8")

        assert "E equals m c squared" in cleaned, "Inline math $E = mc^2$ was not converted!"
        assert "alpha is less than or equal to beta" in cleaned, "Inline math relations were not converted!"
        assert "\\int" not in cleaned, "Display LaTeX equation was not removed!"

        # Run with --keep-display-math
        keep_math_out = Path(tmpdir) / "spoken_math.md"
        main([str(input_file), "-o", str(keep_math_out), "--keep-display-math"])
        spoken_cleaned = keep_math_out.read_text(encoding="utf-8")
        assert "integral from 0 to infinity" in spoken_cleaned, "Display equation was not converted to spoken text with --keep-display-math!"

        # Run with --strip-inline-math
        stripped_math_out = Path(tmpdir) / "stripped_math.md"
        main([str(input_file), "-o", str(stripped_math_out), "--strip-inline-math"])
        stripped_cleaned = stripped_math_out.read_text(encoding="utf-8")
        assert "E equals m c squared" not in stripped_cleaned, "Inline math was not stripped when --strip-inline-math was set!"
    print("✓ test_latex_equations_cleaning passed")


def test_diagrams_and_flowcharts():
    """Verify handling of Mermaid, PlantUML, and ASCII flowcharts/diagrams."""
    sample_text = (
        "# System Architecture\n\n"
        "Here is the workflow diagram:\n\n"
        "```mermaid\n"
        "graph TD\n"
        "    A[Start] --> B[Process]\n"
        "    B --> C[Finish]\n"
        "```\n\n"
        "And here is a PlantUML diagram:\n\n"
        "```plantuml\n"
        "@startuml\n"
        "Alice -> Bob: Authentication Request\n"
        "@enduml\n"
        "```\n\n"
        "Also an ASCII art box:\n\n"
        "+---------+      +---------+\n"
        "| Step 1  | ---> | Step 2  |\n"
        "+---------+      +---------+\n\n"
        "End of document.\n"
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        input_file = Path(tmpdir) / "arch.md"
        input_file.write_text(sample_text, encoding="utf-8")

        # 1. Default: diagram placeholders present
        main([str(input_file)])
        cleaned = (Path(tmpdir) / "arch_cleaned.md").read_text(encoding="utf-8")
        assert "Please refer to the diagram shown in the document." in cleaned
        assert "graph TD" not in cleaned
        assert "+---------+" not in cleaned

        # 2. With --no-placeholders: diagram placeholders omitted
        no_pl_file = Path(tmpdir) / "arch_no_pl.md"
        main([str(input_file), "-o", str(no_pl_file), "--no-placeholders"])
        cleaned_no_pl = no_pl_file.read_text(encoding="utf-8")
        assert "Please refer to the diagram shown in the document." not in cleaned_no_pl
        assert "End of document." in cleaned_no_pl

        # 3. With custom placeholder
        custom_pl_file = Path(tmpdir) / "arch_custom.md"
        main([str(input_file), "-o", str(custom_pl_file), "--diagram-placeholder", "[DIAGRAM_OMITTED]"])
        cleaned_custom = custom_pl_file.read_text(encoding="utf-8")
        assert "[DIAGRAM_OMITTED]" in cleaned_custom
    print("✓ test_diagrams_and_flowcharts passed")


def test_custom_output_and_in_place():
    """Verify custom -o output file and in-place replacement."""
    with tempfile.TemporaryDirectory() as tmpdir:
        input_file = Path(tmpdir) / "original.md"
        input_file.write_text("Hello **world** with $x=1$.", encoding="utf-8")

        # Custom output
        custom_out = Path(tmpdir) / "subdir" / "my_clean.md"
        main([str(input_file), "-o", str(custom_out)])
        assert custom_out.exists()
        assert "Hello world with x equals 1." in custom_out.read_text(encoding="utf-8")

        # In-place replacement
        main([str(input_file), "--in-place"])
        in_place_content = input_file.read_text(encoding="utf-8")
        assert "**world**" not in in_place_content
        assert "Hello world with x equals 1." in in_place_content
    print("✓ test_custom_output_and_in_place passed")


def test_stdout_and_preview(capsys=None):
    """Verify --stdout prints directly without modifying files and --preview works."""
    with tempfile.TemporaryDirectory() as tmpdir:
        input_file = Path(tmpdir) / "preview_test.md"
        input_file.write_text("# Title\n\nPreview text.", encoding="utf-8")

        with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            main([str(input_file), "--stdout"])
            output = mock_stdout.getvalue()
            assert "Title." in output
            assert "Preview text." in output
            assert not (Path(tmpdir) / "preview_test_cleaned.md").exists()

        with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            main([str(input_file), "--preview"])
            output = mock_stdout.getvalue()
            assert "CLEANED PREVIEW: preview_test.md" in output
            assert not (Path(tmpdir) / "preview_test_cleaned.md").exists()
    print("✓ test_stdout_and_preview passed")


def test_batch_directory_and_skips_cleaned():
    """Verify batch processing in a directory skips existing cleaned files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        dir_path = Path(tmpdir)
        (dir_path / "doc1.md").write_text("# Doc 1\n\nContent 1.", encoding="utf-8")
        (dir_path / "doc2.md").write_text("# Doc 2\n\nContent 2.", encoding="utf-8")
        (dir_path / "already_cleaned.md").write_text("Should be skipped.", encoding="utf-8")
        # Give it the _cleaned suffix
        (dir_path / "doc1_cleaned.md").write_text("Existing cleaned file.", encoding="utf-8")

        files = collect_files([str(dir_path)])
        file_names = {f.name for f in files}
        assert "doc1.md" in file_names
        assert "doc2.md" in file_names
        assert "doc1_cleaned.md" not in file_names

        # Run batch clean on directory
        main([str(dir_path)])
        assert (dir_path / "doc2_cleaned.md").exists()
        assert "Doc 2." in (dir_path / "doc2_cleaned.md").read_text(encoding="utf-8")
    print("✓ test_batch_directory_and_skips_cleaned passed")


def test_bengali_cleaning_and_auto_detection():
    """Verify clean_md auto-detects Bengali, converts equations without English speech words, and uses Dari."""
    from pdf.bengali_clean import main as bengali_main

    with tempfile.TemporaryDirectory() as tmpdir:
        bengali_file = Path(tmpdir) / "bengali_doc.md"
        bengali_file.write_text(
            "# 📌 ১. মহাবিশ্বে আলোর পথ\n\n"
            "আইনস্টাইনের সূত্রানুযায়ী:\n"
            "$$\n"
            "n = 1 - \\frac{2}{c^2}\\Phi\n"
            "$$\n\n"
            "- মহাকর্ষীয় বিভব আলোর বেগের বর্গের চেয়ে অনেক কম: $|\\Phi| \\ll c^2$।\n\n"
            "- সূর্যের শোয়ার্জশিল্ড ব্যাসার্ধ $R_S \\approx 2.95 \\text{ km}$।\n",
            encoding="utf-8",
        )

        # 1. Test clean_md with auto-detection
        main([str(bengali_file)])
        cleaned = (Path(tmpdir) / "bengali_doc_cleaned.md").read_text(encoding="utf-8")

        # Verify no English spoken math strings
        assert "is much less than" not in cleaned, "English math string leaked into Bengali!"
        assert "is approximately" not in cleaned, "English math string leaked into Bengali!"
        assert "equals" not in cleaned, "English math string leaked into Bengali!"
        # Verify display math is removed and preceding colon converted to Dari
        assert "\\frac" not in cleaned
        assert "আইনস্টাইনের সূত্রানুযায়ী।" in cleaned or "আইনস্টাইনের সূত্রানুযায়ী:" in cleaned
        # Verify Dari punctuation
        assert "।" in cleaned
        assert "।." not in cleaned, "Glitchy '।.' punctuation was found!"
        # Verify emoji removed
        assert "📌" not in cleaned
        # Verify clean plain notation
        assert "|Phi| << c^2" in cleaned
        assert "R_S ≈ 2.95 km" in cleaned
    print("✓ test_bengali_cleaning_and_auto_detection passed")


def test_bengali_clean_cli_and_example_file():
    """Verify dedicated bengali_clean CLI command and verify on workspace temp.md."""
    from pdf.bengali_clean import main as bengali_main

    temp_md = Path(__file__).resolve().parent.parent / "temp.md"
    if temp_md.exists():
        with tempfile.TemporaryDirectory() as tmpdir:
            out_target = Path(tmpdir) / "temp_cleaned.md"
            bengali_main([str(temp_md), "-o", str(out_target)])
            assert out_target.exists()
            content = out_target.read_text(encoding="utf-8")

            # Check that formulas are cleaned without English speech strings
            assert "the integral from" not in content
            assert "is approximately" not in content
            assert "alpha hat equals" not in content
            assert "।." not in content
            assert "📌" not in content
            assert "💡" not in content
            assert "Effective Refractive Index (n): কার্যকর প্রতিসরাঙ্ক।" in content
    print("✓ test_bengali_clean_cli_and_example_file passed")


if __name__ == "__main__":
    test_default_output_naming()
    test_latex_equations_cleaning()
    test_diagrams_and_flowcharts()
    test_custom_output_and_in_place()
    test_stdout_and_preview()
    test_batch_directory_and_skips_cleaned()
    test_bengali_cleaning_and_auto_detection()
    test_bengali_clean_cli_and_example_file()
    print("\nAll clean_md & bengali_clean tests passed successfully!")
