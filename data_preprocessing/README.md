## data_preprocessing(데이터 정제/전처리 관련 코드)

#### 해당 폴더는 '웹 기반 무인 도서 대여 애플리케이션'에 사용된 데이터셋 정제/전처리 과정을 어떤 방식으로 수행했는지 설명하기 위한 '참고용 폴더'입니다.

***
원본 데이터셋 출처(URL): https://www.bigdata-culture.kr/bigdata/user/data_market/detail.do?id=63513d7b-9b87-4ec1-a398-0a18ecc45411

사용한 원본 데이터셋(URL): https://drive.google.com/drive/folders/1guwcLP3c8PjKyd8F5m-ejNSdSWGYTICx?usp=sharing
***

##### 데이터셋 생성 순서는 다음과 같습니다.

###### 1. data_wrangling.py

원본 데이터셋(도서별 상세정보(202112).csv)으로부터 조에서 설계한 DB 구조에 맞는 컬럼들을 추출합니다.

테스트 편의성을 위하여 image_url 컬럼 외 모두 값이 있는 튜플을 추출하였습니다.

__결과물: 도서별 상세정보_추출본.csv__

---
###### 2. create_publisher_dataset.py

'도서별 상세정보_추출본.csv'으로부터 중복 없이 publisher_name 컬럼을 추출하고, 순서대로 publisher_id 컬럼 데이터를 부여합니다.

__결과물: publisher.csv__

실제 프로젝트에서 사용할 때에는 해당 결과물에 phone_number 컬럼을 엑셀 프로그램에서 직접 추가하여 임의의 데이터(전화번호)를 입력하는 방식으로 진행하였습니다.

---
###### 3. create_bookInfo_dataset.py

'도서별 상세정보_추출본.csv'의 publisher_name 컬럼을 'publisher.csv'의 publisher_id에 맞게 변환(매핑)합니다.

__결과물: bookInfo.csv__

---
### 참고사항

+ __category.csv 파일은 구성이 간단하므로 직접 작성하였습니다.__

+ 위의 방법으로 프로젝트에 사용할 초기 데이터셋을 구성하였고, 백엔드에서 총 3개의 csv 파일을 import 및 임의의 개별 도서를 생성하는 코드를 실행하였습니다.
  + category.csv
  + publisher.csv
  + bookInfo.csv
  + (bookInfo의 각각의 튜플에 해당하는 개별 도서를 생성)

+ 폴더 내의 코드 및 결과물들은 데이터셋 정제/전처리 과정 설명을 위한 참고용 코드로써, Django 폴더 내에 있는 폴더의 csv 파일과 조금의 오차가 있을 수 있습니다.

+ 해당 폴더의 category.csv, publisher.csv, bookInfo.csv 데이터셋을 임포트하여도 정상적으로 애플리케이션이 구동됩니다.
