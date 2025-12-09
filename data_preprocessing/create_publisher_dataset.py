# create_publisher_dataset.py
# 1차적으로 정제/전처리 과정을 마친 추출본으로부터 publisher 릴레이션 생성
# publisher_id, publisher_name 컬럼 생성
# 코드 실행 이후, phone_number 컬럼은 엑셀 편집 프로그램에서 자체적으로 생성하는 방식으로 설정하였습니다.

import pandas as pd
import numpy as np

file_path = '도서별 상세정보_추출본.csv'
save_path = 'publisher.csv'

target_col = 'publisher_name'
id_col_name = 'publisher_id'

# 1. 데이터 불러오기
print(f'{file_path} 읽기 시도...\n')
try:    # 인코딩 에러 방지
    df = pd.read_csv(file_path, encoding='utf-8', low_memory=False)
except UnicodeDecodeError:
    df = pd.read_csv(file_path, encoding='cp949', low_memory=False)

# 2. 필요한 컬럼 추출
print(f'{target_col} -> 필요한 컬럼 추출...\n')
df = df[[target_col]].copy()

# 3. 중복 제거
print(f'{target_col} -> 중복 제거...\n')
df_unique = df.drop_duplicates(subset=target_col, keep='first').reset_index(drop=True)

# 4. id_col_name 생성
print(f'{id_col_name} 생성(1, 2, 3, ...)...\n')
df_unique[id_col_name] = range(1, len(df_unique) + 1)

# 5. 컬럼 순서 재배치
df_unique = df_unique[['publisher_id', 'publisher_name']]

print(df_unique)

print(f'{target_col} -> 중복된 데이터 있는지 검증...\n')
duplicate_val = df_unique[df_unique.duplicated(subset=target_col, keep=False)]

if len(duplicate_val) > 0:
    print(f"\n중복된 {target_col} 발견")
    print(duplicate_val)
    print("결과를 저장하지 않고 종료합니다.")
else:
    print(f"\n{target_col} 검증 완료. {save_path}로 결과를 저장합니다.")
    df_unique.to_csv(save_path, index=False, encoding='utf-8-sig')
    print(f"데이터셋이 저장되었습니다: {save_path}")
