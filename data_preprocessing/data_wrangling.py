# data_wrangling.py
# 원본 데이터셋에서 1차적으로 데이터 정제 및 전처리하여 추출본으로 저장

import pandas as pd
import numpy as np

file_path = '도서별 상세정보(202112).csv'
save_path = '도서별 상세정보_추출본.csv'

target_cols = ['ISBN_THIRTEEN_NO',
               'TITLE_NM',
               'AUTHR_NM',
               'PUBLISHER_NM',
               'IMAGE_URL',
               'KDC_NM'] # 추출할 전체 열

not_null_cols = ['ISBN_THIRTEEN_NO',
                 'TITLE_NM',
                 'AUTHR_NM',
                 'PUBLISHER_NM',
                 'KDC_NM'] # IMAGE_URL -> NULL 허용

length_check_cols = ['TITLE_NM',
                     'AUTHR_NM',
                     'PUBLISHER_NM',
                     'IMAGE_URL']
max_length = 255

rename_map = {
        'ISBN_THIRTEEN_NO': 'isbn',
        'TITLE_NM': 'title',
        'AUTHR_NM': 'author',
        'PUBLISHER_NM': 'publisher_name',
        'IMAGE_URL': 'image_url',
        'KDC_NM': 'category_id'
        }

# 1. 데이터 불러오기
print(f'{file_path} 읽기 시도...\n')
try:    # 인코딩 에러 방지
    df = pd.read_csv(file_path, encoding='utf-8', low_memory=False)
except UnicodeDecodeError:
    df = pd.read_csv(file_path, encoding='cp949', low_memory=False)
    

# 2. 필요한 컬럼 추출
print(f'{target_cols} -> 필요한 컬럼 추출...\n')
df = df[target_cols].copy()


# 3. 데이터 정제: 양 끝 공백 제거
    # 문자열(object) 타입 컬럼에 strip()
print('문자열 데이터 양 끝 공백 제거, 빈 문자열 처리...\n')
for col in target_cols:
    df[col] = df[col].apply(lambda x: x.strip() if isinstance(x, str) else x)

df.replace('', np.nan, inplace=True) # 빈 문자열('') -> NaN으로 치환


# 4. 값이 있는 행만 추출 (IMAGE_URL 제외)
print(f'{not_null_cols} -> 값이 있는 행만 추출...\n')
df = df.dropna(subset=not_null_cols)


# 5. 글자수 제한 필터링 (max_length 이하) -> length_check_cols 대상
print(f'{length_check_cols} -> {max_length}자 이하 행만 추출...\n')
condition = pd.Series([True] * len(df), index=df.index) # IMAGE_URL은 값이 없는(NaN) 경우 통과

for col in length_check_cols:
    # pd.notna(x)로 값이 존재할 때만 길이 체크, 없으면 True(통과)
    condition = condition & df[col].apply(lambda x: len(str(x)) <= max_length if pd.notna(x) else True)

df = df[condition]


# 6. KDC_NM 대분류 변환 (예: 885.2 -> 800)
def transform_kdc(kdc):
    try:
        num = float(kdc)
        main_class = int(num // 100) * 100 # 885.2 // 100 = 8.0  -> 8.0 * 100 = 800
        
        return str(main_class)
    except:
        return np.nan

print('세부 분류 -> 대분류(100단위) 변환 중... (변환 실패한 행은 제거)\n')
df['KDC_NM'] = df['KDC_NM'].apply(transform_kdc)
df = df.dropna(subset=['KDC_NM']) # 변환 실패(NaN) 행 제거


# 7. 데이터 검증
print("\n" + "="*30)
print("1. 데이터프레임 세부 정보 (Info)")
print("="*30)
print(df.info())

print("\n" + "="*30)
print(f"2. 컬럼별 최대 글자수 확인 (Max Limit: {max_length})")
print("="*30)
is_valid_length = True
for col in df.columns:
    # 각 컬럼의 값을 문자열로 변환하여 길이를 측정 (NaN은 0으로 처리)
    max_len = df[col].apply(lambda x: len(str(x)) if pd.notna(x) else 0).max()
    print(f"- {col}: {max_len}자")
    
    if max_len > max_length and col in length_check_cols:
        is_valid_length = False
        print(f"  [경고] {col} 컬럼이 제한 길이를 초과했습니다!")

print("\n" + "="*30)
print("3. 컬럼명 변경 및 파일 저장")
print("="*30)


# 데이터가 존재하고 길이 제한에 문제가 없으면 저장 (강제 저장하려면 조건문 제거 가능)
if not df.empty:
    #rename_map
    print(f"컬럼명을 변경합니다: {list(rename_map.values())}")
    df = df.rename(columns=rename_map)
    
    # 저장
    df.to_csv(save_path, index=False, encoding='utf-8-sig')
    print(f"파일이 성공적으로 저장되었습니다: {save_path}")
    
    # 변경된 컬럼명 확인
    print("\n[저장된 데이터 미리보기]")
    print(df.head(3))
else:
    print("저장할 데이터가 없거나 데이터프레임이 비어 있습니다.")
