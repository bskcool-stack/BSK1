"""
CSV 파일 로딩 및 인코딩 처리 모듈
"""

import pandas as pd
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def load_csv(file_path: str, encodings: Optional[list] = None) -> pd.DataFrame:
    """
    CSV 파일을 로드하고 적절한 인코딩으로 파싱
    
    Parameters
    ----------
    file_path : str
        로드할 CSV 파일 경로
    encodings : list, optional
        시도할 인코딩 리스트. 기본값: ['cp949', 'euc-kr', 'utf-8-sig', 'utf-8']
    
    Returns
    -------
    pd.DataFrame
        로드된 데이터프레임
    
    Raises
    ------
    FileNotFoundError
        파일이 존재하지 않는 경우
    ValueError
        지원되는 인코딩으로 파일을 읽을 수 없는 경우
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_path}")
    
    if encodings is None:
        encodings = ['cp949', 'euc-kr', 'utf-8-sig', 'utf-8']
    
    last_error = None
    for encoding in encodings:
        try:
            logger.info(f"'{encoding}' 인코딩으로 파일 로드 시도: {file_path.name}")
            df = pd.read_csv(file_path, encoding=encoding)
            logger.info(f"[OK] '{encoding}' 인코딩으로 파일 로드 성공 (행: {len(df)}, 열: {len(df.columns)})")
            return df
        except (UnicodeDecodeError, LookupError) as e:
            last_error = e
            logger.debug(f"[FAIL] '{encoding}' 인코딩 실패: {str(e)}")
            continue
    
    raise ValueError(
        f"지원되는 인코딩으로 파일을 읽을 수 없습니다: {file_path}\n"
        f"시도한 인코딩: {', '.join(encodings)}\n"
        f"마지막 오류: {last_error}"
    )


def get_file_info(file_path: str) -> dict:
    """
    CSV 파일의 기본 정보 반환
    
    Parameters
    ----------
    file_path : str
        파일 경로
    
    Returns
    -------
    dict
        파일 정보 (크기, 행 수, 열 수 등)
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_path}")
    
    df = load_csv(str(file_path))
    
    return {
        'file_name': file_path.name,
        'file_size_kb': file_path.stat().st_size / 1024,
        'rows': len(df),
        'columns': len(df.columns),
        'column_names': df.columns.tolist(),
        'memory_usage_mb': df.memory_usage(deep=True).sum() / (1024 ** 2)
    }

