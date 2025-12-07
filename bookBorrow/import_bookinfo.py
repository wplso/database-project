import os
import django
import pandas as pd
from tqdm import tqdm

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bookBorrow.settings')
django.setup()

from bookdb.models import BookInfo, Category, Publisher

def import_bookinfo_from_csv(filepath):
    df = pd.read_csv(filepath)
    df = df.where(pd.notna(df), None)

    print("BookInfo 임포트 시작")

    created_count = 0
    existing_count = 0
    skipped_fk_count = 0
    skipped_error_count = 0
    skipped_length_count = 0

    for index, row in tqdm(df.iterrows(), total=len(df), desc="BookInfo 처리 중"):
        try:
            isbn_from_csv = row['isbn']
            title_from_csv = row['title']
            author_from_csv = row['author']
            category_id_from_csv = row['category_id']
            publisher_id_from_csv = row['publisher_id']
            image_url = row.get('image_url')

            if not isbn_from_csv or not title_from_csv or pd.isna(category_id_from_csv) or pd.isna(publisher_id_from_csv):
                skipped_fk_count += 1
                continue
            
            if len(str(title_from_csv)) > 255:
                skipped_length_count += 1
                continue

            if author_from_csv and len(str(author_from_csv)) > 50:
                skipped_length_count += 1
                continue

            category_obj = Category.objects.get(category_id=category_id_from_csv)
            publisher_obj = Publisher.objects.get(publisher_id=publisher_id_from_csv)

            book, created = BookInfo.objects.get_or_create(
                isbn=isbn_from_csv,
                
                defaults={
                    'title': title_from_csv,
                    'author': author_from_csv,
                    'category': category_obj,
                    'publisher': publisher_obj,
                    'image_url': image_url if image_url else None
                }
            )
            
            if created:
                created_count += 1
            else:
                existing_count += 1

        except (Category.DoesNotExist, Publisher.DoesNotExist):
            skipped_fk_count += 1
        
        except Exception as e:
            skipped_error_count += 1

    print("BookInfo 임포트 완료.")
    print(f"  - 총 {len(df)}건 시도")
    print(f"  - {created_count}건 생성 완료")
    print(f"  - {existing_count}건은 이미 존재함")
    print(f"  - {skipped_length_count}건 스킵 (원인: 제목 또는 저자 길이 초과)")
    print(f"  - {skipped_fk_count}건 스킵 (원인: 유효하지 않은 FK 또는 필수 값 누락)")
    print(f"  - {skipped_error_count}건 스킵 (원인: 기타 오류)")

if __name__ == "__main__":
    csv_file_path = 'bookInfo.csv'
    import_bookinfo_from_csv(csv_file_path)
