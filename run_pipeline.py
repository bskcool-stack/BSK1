"""
데이터 파이프라인 실행 스크립트
"""

import sys
import logging
from pathlib import Path

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


def main():
    """메인 실행 함수"""
    from src.transform import run_pipeline as run_phase1
    from src.metrics import run_aggregation_pipeline
    
    # 파일 경로 설정
    input_csv = "서울교통공사_지하철혼잡도정보_20250930.csv"
    output_parquet = "data/processed/congestion_long.parquet"
    output_report = "data/processed/data_quality_report.json"
    
    # Phase 1: 데이터 변환 파이프라인
    logger.info("\n>>> Phase 1: 데이터 로딩/정리 파이프라인 시작")
    
    # 파일 존재 확인
    if not Path(input_csv).exists():
        logger.error(f"입력 파일을 찾을 수 없습니다: {input_csv}")
        sys.exit(1)
    
    try:
        # Phase 1 파이프라인 실행
        df_long, report = run_phase1(input_csv, output_parquet, output_report)
        
        # Phase 1 결과 요약 출력
        print("\n" + "=" * 60)
        print("Phase 1: 데이터 변환 결과 요약")
        print("=" * 60)
        print(f"전체 행 수: {report['total_rows']:,}")
        print(f"고유 역 수: {report.get('unique_stations', 'N/A')}")
        print(f"노선 수: {report.get('unique_lines', 'N/A')}")
        print(f"시간대 수: {report.get('time_slots', 'N/A')}")
        
        if 'congestion_stats' in report:
            stats = report['congestion_stats']
            print(f"\n혼잡도 통계:")
            print(f"  평균: {stats['mean']:.1f}")
            print(f"  최소: {stats['min']:.1f}")
            print(f"  최대: {stats['max']:.1f}")
            print(f"  중앙값: {stats['median']:.1f}")
        
        if report.get('null_count'):
            print(f"\n결측값:")
            for col, count in report['null_count'].items():
                print(f"  {col}: {count:,}")
        
        print("\n[성공] Phase 1 완료!")
        print(f"  출력 파일: {output_parquet}")
        print(f"  리포트: {output_report}")
        print("=" * 60)
        
        # Phase 2: 집계 파이프라인
        logger.info("\n>>> Phase 2: 집계/캐시 레이어 시작")
        
        aggregation_results = run_aggregation_pipeline(
            input_path=output_parquet,
            output_dir="data/processed"
        )
        
        # Phase 2 결과 요약 출력
        print("\n" + "=" * 60)
        print("Phase 2: 집계 결과 요약")
        print("=" * 60)
        for key, df in aggregation_results.items():
            print(f"{key}: {len(df):,} 행")
        
        print("\n[성공] Phase 2 완료!")
        print("  생성된 집계 파일:")
        print("    - line_time_avg.parquet")
        print("    - station_time_avg.parquet")
        print("    - top_congested.parquet")
        print("    - top_least_congested.parquet")
        print("    - peak_times.parquet")
        print("=" * 60)
        
        print("\n" + "=" * 60)
        print("전체 파이프라인 실행 완료!")
        print("=" * 60)
        
    except Exception as e:
        logger.error(f"파이프라인 실행 중 오류 발생: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

