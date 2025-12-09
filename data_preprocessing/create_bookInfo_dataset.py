# create_bookInfo_dataset.py
# 추출본에서의 publisher_name -> publisher_id로 변환(매핑)
# 추출본 및 publisher.csv 파일이 생성되어 있어야함

import pandas as pd
import numpy as np

book_file_path = '도서별 상세정보_추출본.csv'
publisher_file_path = 'publisher.csv'
save_path = 'bookInfo.csv'

# 1. book_file_path, publisher_file_path 데이터 불러오기
print(f'{book_file_path} 읽기 시도...\n')
try:    # 인코딩 에러 방지
    df = pd.read_csv(book_file_path, encoding='utf-8', low_memory=False)
except UnicodeDecodeError:
    df = pd.read_csv(book_file_path, encoding='cp949', low_memory=False)

print(f'{publisher_file_path} 읽기 시도...\n')
try:    # 인코딩 에러 방지
    publisher_df = pd.read_csv(publisher_file_path, encoding='utf-8', low_memory=False)
except UnicodeDecodeError:
    publisher_df = pd.read_csv(publisher_file_path, encoding='cp949', low_memory=False)

# 2. publisher_name -> publisher_id 매핑
print(f'publisher_name -> publisher_id 매핑...\n')
merged_df = df.merge(publisher_df, on='publisher_name', how='left')

# 3. 매핑되지 않은 출판사 검증 및 저장
unmatched = merged_df[merged_df['publisher_id'].isna()]['publisher_name'].unique()
if len(unmatched) > 0:
    print("\n 매핑되지 않은 publisher_name 발견.")
    for name in unmatched:
        print(" -", name)
    print(f"{publisher_file_path}에 없는 출판사가 존재합니다. 결과를 저장하지 않고 종료합니다.")
else:
    print("모든 publisher_name이 정상적으로 publisher_id로 매핑되었습니다.")
    merged_df = merged_df.drop(columns=['publisher_name'])
    merged_df = merged_df[['isbn', 'title', 'author', 'category_id', 'publisher_id', 'image_url']]
    merged_df.to_csv(save_path, index=False, encoding='utf-8-sig')
    print(f"{save_path}에 저장이 완료되었습니다.")

