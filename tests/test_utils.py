import pandas as pd

from jiraproject.utils_normalize import normalize, canonical_type
from jiraproject.utils_dates import compute_days_resolution
from jiraproject.utils_arrow import to_arrow_safe_numeric, make_display_copy
from jiraproject.utils_constants import TIPOS_AGEIS_CANON


def test_normalize_and_canonical_type():
    assert normalize('História') == normalize('Historia')
    assert canonical_type(normalize('Historia')) == 'História'
    assert canonical_type(normalize('Debito Tecnico')) == 'Débito Técnico'
    assert canonical_type(normalize('Spike')) == 'Spike'


def test_compute_days_resolution():
    df = pd.DataFrame({
        'Data Criação': pd.to_datetime(['2025-01-01', None, '2025-01-03']),
        'Data Resolução': pd.to_datetime(['2025-01-06', '2025-01-02', None]),
    })
    df = compute_days_resolution(df, 'Data Criação', 'Data Resolução')
    assert df['Dias para Resolução'].iloc[0] == 5
    assert pd.isna(df['Dias para Resolução'].iloc[1])
    assert pd.isna(df['Dias para Resolução'].iloc[2])


def test_arrow_safe_display_copy():
    df = pd.DataFrame({
        'SP': [3, 5, 8],
        'História': [1.234, None, 3.0],
        'Débito Técnico': [None, 5.5, 2.2],
    })
    df = to_arrow_safe_numeric(df, ['História', 'Débito Técnico'])
    disp = make_display_copy(df, ['História', 'Débito Técnico'], decimals=1)
    assert disp['História'].tolist() == [1.2, '—', 3.0]
    assert disp['Débito Técnico'].tolist() == ['—', 5.5, 2.2]


def test_tipos_ageis_const():
    assert 'História' in TIPOS_AGEIS_CANON
    assert 'Débito Técnico' in TIPOS_AGEIS_CANON
    assert 'Spike' in TIPOS_AGEIS_CANON

"""
Testes para o módulo credcesta.utils
"""
import pytest
from credcesta.utils import sanitize_filename


class TestSanitizeFilename:
    """Testes para a função sanitize_filename."""
    
    def test_remove_brackets(self):
        """Testa remoção de colchetes."""
        result = sanitize_filename("[DIGITAL] Test")
        assert result == "DIGITAL_Test"
    
    def test_replace_slashes(self):
        """Testa substituição de barras por underscore."""
        result = sanitize_filename("Sites / Marketing")
        assert result == "Sites_Marketing"
    
    def test_replace_spaces(self):
        """Testa substituição de espaços por underscore."""
        result = sanitize_filename("Test File Name")
        assert result == "Test_File_Name"
    
    def test_remove_special_characters(self):
        """Testa remoção de caracteres especiais."""
        result = sanitize_filename("Test@File#Name$")
        assert result == "Test_File_Name"
    
    def test_preserve_valid_characters(self):
        """Testa preservação de caracteres válidos."""
        result = sanitize_filename("Test_File-Name.csv")
        assert result == "Test_File-Name.csv"
    
    def test_remove_multiple_underscores(self):
        """Testa remoção de underscores múltiplos."""
        result = sanitize_filename("Test___File___Name")
        assert result == "Test_File_Name"
    
    def test_strip_leading_trailing_underscores(self):
        """Testa remoção de underscores no início e fim."""
        result = sanitize_filename("_Test_File_")
        assert result == "Test_File"
    
    def test_complex_filename(self):
        """Testa caso complexo similar ao erro real."""
        result = sanitize_filename("[DIGITAL] Sites / Marketing_4450_analysis.csv")
        assert result == "DIGITAL_Sites_Marketing_4450_analysis.csv"
    
    def test_empty_string(self):
        """Testa string vazia."""
        result = sanitize_filename("")
        assert result == ""
    
    def test_only_special_characters(self):
        """Testa string com apenas caracteres especiais."""
        result = sanitize_filename("@#$%^&*()")
        assert result == ""
    
    def test_parentheses_and_other_chars(self):
        """Testa parênteses e outros caracteres."""
        result = sanitize_filename("Test (Copy) [2024].txt")
        assert result == "Test_Copy_2024.txt"