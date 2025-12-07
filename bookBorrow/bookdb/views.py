from django.shortcuts import render
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate, login, update_session_auth_hash
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.hashers import make_password
from django.db import IntegrityError, transaction
from .models import Member, BookInfo, Publisher, Category, Book, Borrow, Review, Policy
from django.db.models import Q, Count, Case, When, BooleanField, Avg
from datetime import date, timedelta
from django.core.exceptions import ValidationError
from django.contrib.auth import logout
from django.db.models import ProtectedError


@csrf_exempt #Postman으로 API 테스트를 할 수 있게 CSRF 검증을 임시로 끈다. 
#회원가입
def signup(request):
    #회원가입은 POST 요청으로만 처리
    if request.method == 'POST':
        try:
            #요청의 body에 담긴 JSON 데이터를 파이썬 딕셔너리로 변환
            data = json.loads(request.body)
            #AbstractUser의 필수 필드 및 커스텀 필드 가져오기
            login_id = data['login_id']
            password = data['password']
            first_name = data['first_name']
            email = data['email']
            birth_date = data['birth_date']
            phone_number = data['phone_number']

 # (수정)중복 검사 로직을 명시적으로 분리 (정확한 에러 메시지를 위해)
            if Member.objects.filter(login_id=login_id).exists():
                return JsonResponse({"error": "이미 존재하는 아이디입니다.", "errorcode": 1}, status=400)
            
            if Member.objects.filter(email=email).exists():
                return JsonResponse({"error": "이미 가입된 이메일입니다.", "errorcode": 2}, status=400)
            
            if Member.objects.filter(phone_number=phone_number).exists():
                return JsonResponse({"error": "이미 가입된 전화번호입니다.", "errorcode": 3}, status=400)
            #Member 모델로 객체를 생성하고 DB에 INSERT
            new_member = Member.objects.create_user(
                login_id=login_id,
                password=password,
                first_name=first_name,
                email=email,
                birth_date=birth_date,
                phone_number=phone_number
                #status는 default='정상'이므로 생략 가능
            )
            #성공 응답 반환 (HTTP 201 Created)
            return JsonResponse({"message": "회원가입 성공!",
                "created_user_id": new_member.login_id,  # 아이디
                "created_user_name": new_member.first_name, # 이름
                "pk": new_member.pk # 내부 관리 번호 (id)
                }, status=201)
                

        #ID 중복 오류 (login_id가 unique=True이므로)
        except IntegrityError as e:
            print("IntegrityError:", e)
            return JsonResponse({"error": "이미 존재하는 아이디입니다."}, status=400)

        
        #JSON 데이터에 필수 키가 빠졌을 경우
        except KeyError:
            return JsonResponse({"error": "필수 값이 누락되었습니다."}, status=400)
        
        #JSON 형식이 아닐 경우
        except json.JSONDecodeError:
            return JsonResponse({"error": "잘못된 JSON 형식입니다."}, status=400)

    #POST가 아닌 GET 등의 요청이 오면 에러 반환
    else:
        return JsonResponse({"error": "POST 요청만 허용됩니다."}, status=405)
    

@csrf_exempt
#로그인
def login_user(request):
    if request.method != 'POST':
        return JsonResponse({"error": "POST 요청만 허용됩니다."}, status=405)

    try:
        data = json.loads(request.body)
        login_id = data['login_id']
        password = data['password']
    except (KeyError, json.JSONDecodeError):
        return JsonResponse({"error": "login_id와 password가 필요합니다."}, status=400)

    #Django의 authenticate 사용
    #Member 모델의 USERNAME_FIELD='login_id'를 자동으로 인식하여 인증
    user = authenticate(request, login_id=login_id, password=password)

    if user is not None:  
        #user 객체가 유효하면 인증 성공
        #login 함수로 세션을 생성하고 쿠키를 브라우저에 전송
        login(request, user)
        
        # 연체 기간이 지났는지 확인하고 상태 복구
        if user.status == "대여정지" and user.overdue_end_date and date.today() > user.overdue_end_date:
            user.status = "정상"
            user.overdue_end_date = None
            user.save()

        return JsonResponse({
            "message": "로그인 성공!",
            "user": {
                "login_id": user.login_id,
                "first_name": user.first_name,
                "email": user.email,
                "superuser": user.is_superuser,
                "staff": user.is_staff
            }
        }, status=200)
    else:
        #user가 None이면 인증 실패
        return JsonResponse({"error": "아이디 또는 비밀번호가 올바르지 않습니다."}, status=401)
@csrf_exempt    
#로그아웃
def logout_user(request):
    logout(request)

    return JsonResponse({"message": "로그아웃 성공"})

@csrf_exempt
#회원정보수정
def update_member_info(request):
    if request.method != 'POST':
        return JsonResponse({"error": "POST 요청만 허용됩니다."}, status=405)

    #로그인한 사용자인지 확인
    if not request.user.is_authenticated:
        return JsonResponse({"error": "로그인이 필요합니다."}, status=401)

    try:
        #로그인된 사용자 객체를 바로 가져옴
        data = json.loads(request.body)
        user = request.user

        #고유(unique) 값 중복 확인(이메일이나 전화번호가 다른 사람과 중복되면 안 됨)
        
        if 'email' in data:
            new_email = data['email']
            #email이 unique=True이므로, 나를 제외한 다른 사람 중에 중복이 있는지 확인
            if Member.objects.filter(email=new_email).exclude(pk=user.pk).exists():
                return JsonResponse({"error": "이미 사용 중인 이메일입니다."}, status=400)
            user.email = new_email

        if 'phone_number' in data:
            new_phone = data['phone_number']
            #phone_number가 unique=True이므로, 나를 제외한 다른 사람 중에 중복이 있는지 확인
            if Member.objects.filter(phone_number=new_phone).exclude(pk=user.pk).exists():
                return JsonResponse({"error": "이미 사용 중인 전화번호입니다."}, status=400)
            user.phone_number = new_phone
        
        # 생년월일 수정 (YYYY-MM-DD 형식)
        if 'birth_date' in data:
            user.birth_date = data['birth_date'] 

        #이름 정보 업데이트
        if 'first_name' in data:
            user.first_name = data['first_name']

        # 변경사항 DB에 저장
        user.save()

        return JsonResponse({
            "message": "회원 정보가 성공적으로 수정되었습니다.",
            "user": {
                "login_id": user.login_id,
                "first_name": user.first_name,
                "email": user.email,
                "phone_number": user.phone_number,
                "birth_date": user.birth_date
            }
        }, status=200)

    except (KeyError, json.JSONDecodeError):
        return JsonResponse({"error": "잘못된 요청 형식입니다."}, status=400)
    except Exception as e:
        return JsonResponse({"error": f"수정 중 오류 발생: {str(e)}"}, status=500)
    
@csrf_exempt
#비밀번호 변경
def change_password(request):
    if request.method != 'POST':
        return JsonResponse({"error": "POST 요청만 허용됩니다."}, status=405)

    if not request.user.is_authenticated:
        return JsonResponse({"error": "로그인이 필요합니다."}, status=401)

    try:
        data = json.loads(request.body)
        current_password = data['current_password']
        new_password = data['new_password']
    except (KeyError, json.JSONDecodeError):
        return JsonResponse({"error": "current_password와 new_password가 필요합니다."}, status=400)

    user = request.user

    #현재 비밀번호가 맞는지 확인
    if not user.check_password(current_password):
        return JsonResponse({"error": "현재 비밀번호가 일치하지 않습니다."}, status=403)

    try:
        #새 비밀번호가 Django의 보안 정책에 맞는지 검사
        validate_password(new_password, user=user)
    except ValidationError as e:
        #예: "비밀번호가 너무 짧습니다." 등
        return JsonResponse({"error": list(e.messages)}, status=400)

    #새 비밀번호로 변경 (자동으로 해시됨)
    user.set_password(new_password)
    user.save()

    #세션 갱신
    #안하면 비밀번호 변경 후 바로 로그아웃됨
    update_session_auth_hash(request, user)

    return JsonResponse({"message": "비밀번호가 성공적으로 변경되었습니다."}, status=200)

#마이페이지
def my_info(request):
    #GET 요청으로만 처리
    if request.method != 'GET':
        return JsonResponse({"error": "GET 요청만 허용됩니다."}, status=405)

    #로그인한 사용자인지 확인
    if not request.user.is_authenticated:
        return JsonResponse({"error": "로그인이 필요합니다."}, status=401)
        
    user = request.user

    #Member 모델의 정보를 JSON으로 반환
    return JsonResponse({
        "id": user.id,
        "login_id": user.login_id,
        "first_name": user.first_name,
        "email": user.email,
        "phone_number": user.phone_number,
        "birth_date": user.birth_date,
        "status": user.status,
        "overdue_end_date": user.overdue_end_date, 
        "is_staff": user.is_staff, # 관리자 여부(회원 관리/도서 편집 활성화 여부)
    }, status=200)

#내 대여/반납 내역 (마이페이지)
def my_borrows(request):
    if request.method != 'GET':
        return JsonResponse({"error": "GET 요청만 허용됩니다."}, status=405)

    #로그인한 사용자인지 확인
    if not request.user.is_authenticated:
        return JsonResponse({"error": "로그인이 필요합니다."}, status=401)
        
    user = request.user

    #로그인한 사용자를 기준으로 Borrow 테이블 검색
    #(select_related: FK로 연결된 Book, BookInfo 테이블을 미리 JOIN하여 DB 성능 향상)
    borrows_queryset = Borrow.objects.filter(member=user).select_related(
        'book', 'book__isbn'
    ).order_by('-borrow_date') # 최신 대여 순으로 정렬

    #.values()를 사용해 딕셔너리 리스트로 변환
    borrows_list = list(borrows_queryset.values(
        'borrow_id',
        'borrow_date',
        'due_date',
        'return_date',      # 반납 안했으면 null
        'is_extended',
        'book__book_manage_id', # 실물 도서 관리 번호
        'book__isbn__title',    # Book -> BookInfo -> title
        'book__isbn__author',    # Book -> BookInfo -> author
        'book__isbn__image_url'
    ))
    
    return JsonResponse({'borrows': borrows_list}, status=200)

#내가 쓴 리뷰 목록 (마이페이지)
def my_reviews(request):
    if request.method != 'GET':
        return JsonResponse({"error": "GET 요청만 허용됩니다."}, status=405)

    #로그인한 사용자인지 확인
    if not request.user.is_authenticated:
        return JsonResponse({"error": "로그인이 필요합니다."}, status=401)
        
    user = request.user

    #로그인한 사용자를 기준으로 Review 테이블 검색
    #(select_related: 'isbn' (BookInfo)을 미리 JOIN)
    reviews_queryset = Review.objects.filter(member=user).select_related(
        'isbn'
    ).order_by('-created_at') # 최신 리뷰 순으로 정렬

    #.values()를 사용해 딕셔너리 리스트로 변환
    reviews_list = list(reviews_queryset.values(
        'review_id',
        'rating',
        'content',
        'created_at',
        'isbn__isbn',    # 리뷰 대상 책의 ISBN
        'isbn__title',    # 리뷰 대상 책의 제목
        'isbn__image_url'
    ))
    
    return JsonResponse({'reviews': reviews_list}, status=200)

#회원 탈퇴
@csrf_exempt
def delete_account(request):
    if request.method != 'POST':
        return JsonResponse({"error": "POST 요청만 허용됩니다."}, status=405)

    #로그인한 사용자인지 확인
    if not request.user.is_authenticated:
        return JsonResponse({"error": "로그인이 필요합니다."}, status=401)
        
    user = request.user

    try:
        data = json.loads(request.body)
        password = data['password'] # 본인 확인을 위한 비밀번호
    except (KeyError, json.JSONDecodeError):
        return JsonResponse({"error": "본인 확인을 위해 'password'가 필요합니다."}, status=400)

    #현재 비밀번호가 맞는지 확인
    if not user.check_password(password):
        return JsonResponse({"error": "비밀번호가 일치하지 않습니다."}, status=403)

    try:
        #데이터 삭제(DELETE) 대신 '비활성화' 처리
        #(Member의 is_active=False가 되면 Django의 authenticate가 차단)
        user.is_active = False
        user.status = "탈퇴"
        user.save()

        #세션 종료 (로그아웃)
        logout(request)
        
        return JsonResponse({"message": "회원 탈퇴 처리가 완료되었습니다."}, status=200)

    except Exception as e:
        return JsonResponse({"error": f"탈퇴 처리 중 오류 발생: {str(e)}"}, status=500)

#단일 도서 상세정보
def book_detail(request, isbn): # URL로부터 isbn 값을 받음
    
    if request.method != 'GET':
        return JsonResponse({"error": "GET 요청만 허용됩니다."}, status=405)

    try:
        #(검색) PK(isbn)로 BookInfo를 찾음
        #(select_related: Category, Publisher를 미리 JOIN)
        book = BookInfo.objects.select_related(
            'category', 'publisher'
        ).get(isbn=isbn)

        # 도서의 리뷰 평균 평점 계산
        # result = {'rating__avg': 4.5} 형태로 반환됨. 리뷰 없으면 None
        avg_data = Review.objects.filter(isbn=book).aggregate(Avg('rating'))
        avg_rating = avg_data['rating__avg']

        #(반환) 책 상세 정보를 JSON으로 반환
        return JsonResponse({
            'isbn': book.isbn,
            'title': book.title,
            'author': book.author,
            'publisher_name': book.publisher.publisher_name if book.publisher else None,
            'category_name': book.category.category_name if book.category else None,
            'image_url': book.image_url,
            'rating': round(avg_rating, 1) if avg_rating else 0.0 # 소수점 1자리로 반올림하여 반환
        }, status=200)

    except BookInfo.DoesNotExist:
        return JsonResponse({"error": "존재하지 않는 책(ISBN)입니다."}, status=404)
    except Exception as e:
        return JsonResponse({"error": f"데이터를 불러오는 중 오류 발생: {str(e)}"}, status=500)

#도서 검색
def search_books(request):
    if request.method == 'GET':
        
        #URL에서 'q'라는 이름의 쿼리 파라미터 값을 가져옴 (예: /api/books/?q=검색어)
        #값이 없으면 빈 문자열(None)을 반환
        query = request.GET.get('q', None)
        
        if query:
            #Q 객체를 사용하여 'OR' 조건 검색
            #icontains = 대소문자 구분 없이 '포함' (SQL의 LIKE '%...%')
            #publisher__publisher_name = BookInfo의 publisher(FK)를 통해 Publisher의 publisher_name 검색
            search_condition = (
                Q(title__icontains=query) |
                Q(author__icontains=query) |
                Q(publisher__publisher_name__icontains=query) |
                Q(isbn__icontains=query)
            )
            
            #BookInfo 테이블에서 조건에 맞는 책들을 검색 (수량 반영)
            queryset = BookInfo.objects.filter(search_condition).annotate(
                stock_count=Count('book', filter=Q(book__status=Book.Status.AVAILABLE))
            )
            
            #.values()를 사용해 검색 결과를 Python 딕셔너리 리스트로 변환
            #(ForeignKey 필드는 __를 사용해 접근)
            results = list(queryset.values(
                'isbn', 
                'title', 
                'author', 
                'publisher__publisher_name', 
                'category__category_name',
                'image_url',
                'stock_count'
            ))
            
            return JsonResponse({'books': results}, status=200)
        
        else:
            #검색어가 없으면 빈 리스트 반환
            return JsonResponse({'books': []}, status=200)

    #GET 요청이 아니면 에러 반환
    else:
        return JsonResponse({"error": "GET 요청만 허용됩니다."}, status=405)

@csrf_exempt
#도서 대여
def borrow_books(request):
    if request.method != 'POST':
        return JsonResponse({"error": "POST 요청만 허용됩니다."}, status=405)
    
    if not request.user.is_authenticated:
        return JsonResponse({"error": "로그인이 필요합니다."}, status=401)
    
    try:
        data = json.loads(request.body)
        isbn_list = data['isbns'] #대여할 책들의 ISBN 리스트
        member = request.user

        # 연체 기간이 지났는지 확인하고 상태 복구
        if member.status == "대여정지" and member.overdue_end_date and date.today() > member.overdue_end_date:
            member.status = "정상"
            member.overdue_end_date = None
            member.save()

        #회원 상태(status) 확인
        if member.status == "대여정지":
            return JsonResponse({
                "error": "회원님이 현재 '대여정지' 상태이므로 대여할 수 없습니다.",
                "overdue_end_date": member.overdue_end_date
            }, status=403)

    except (KeyError, json.JSONDecodeError):
        return JsonResponse({"error": "잘못된 요청 형식입니다. isbns 리스트가 필요합니다."}, status=400)
    
    policy = Policy.load()

    #최대 대여 권수 확인
    current_borrow_count = Borrow.objects.filter(member=request.user, return_date__isnull=True).count()
    if current_borrow_count + len(isbn_list) > policy.max_borrow_count:
        return JsonResponse({"error": f"최대 {policy.max_borrow_count}권까지만 대여할 수 있습니다."}, status=400)
    
    # ---대여 처리 시작---
    successful_borrows = []
    failed_borrows = []
    today = date.today()
    due_date = today + timedelta(days=policy.default_due_days) #기본 대여 기간 14일

    #for 루프 전체를 'transaction.atomic'으로 감싼다.
    #루프 중간에 하나라도 오류가 나면 모든 작업이 롤백(취소)된다.
    try:
        with transaction.atomic():
            for isbn in isbn_list:
                available_copy = None
                
                #대여 가능한 실물 책(Book)을 찾는다. (BookInfo(isbn)가 아니라 Book(실물)을 찾음.)
                #.select_for_update(): 다른 사람이 동시에 이 책을 대여하지 못하도록 잠금을 건다.
                available_copy = Book.objects.select_for_update().filter(
                    isbn_id=isbn,       # BookInfo의 ISBN을 참조
                    status=Book.Status.AVAILABLE #0, status가 '대여가능' 상태여야 함
                ).first() #.first() = 조건에 맞는 책 중 첫 번째 1권

                if available_copy:
                    #(성공) 대여 가능한 책을 찾았을 경우
                    
                    #Borrow 테이블에 대여 기록 INSERT
                    Borrow.objects.create(
                        member=member,
                        book=available_copy, # 'isbn'이 아닌 'available_copy' 객체
                        borrow_date=today,
                        due_date=due_date
                        #is_extended는 default=False
                    )
                    
                    #Book 테이블의 상태를 '대여중'으로 변경
                    available_copy.status = Book.Status.BORROWED #1
                    available_copy.save()
                    
                    successful_borrows.append(isbn)
                
                else:
                    #(실패) 대여 가능한 책이 없을 경우
                    failed_borrows.append(isbn)
    
    except Exception as e:
        #트랜잭션 도중 알 수 없는 오류가 발생하면 롤백됨
        print(e)
        return JsonResponse({"error": f"대여 처리 중 오류 발생: {str(e)}"}, status=500)

    #최종 결과 반환
    return JsonResponse({
        "message": "대여 처리가 완료되었습니다.",
        "successful_isbns": successful_borrows,
        "failed_isbns": failed_borrows
    }, status=200)


#대여 연장
@csrf_exempt
def extend_borrow(request):
    if request.method != 'POST':
        return JsonResponse({"error": "POST 요청만 허용됩니다."}, status=405)

    if not request.user.is_authenticated:
        return JsonResponse({"error": "로그인이 필요합니다."}, status=401)

    try:
        data = json.loads(request.body)
        borrow_id = data['borrow_id'] # 연장할 대여 기록의 ID
        
        #DB에서 대여 기록을 찾음
        borrow = Borrow.objects.get(borrow_id=borrow_id)

    except (KeyError, json.JSONDecodeError):
        return JsonResponse({"error": "borrow_id가 필요합니다."}, status=400)
    except Borrow.DoesNotExist:
        return JsonResponse({"error": "존재하지 않는 대여 기록입니다."}, status=404)

    #(보안) 이 대여 기록이 로그인한 사용자의 것인지 확인
    if borrow.member != request.user:
        return JsonResponse({"error": "본인의 대여 기록만 연장할 수 있습니다."}, status=403)

    # 이미 반납했는지 확인
    if borrow.return_date is not None:
        return JsonResponse({"error": "이미 반납된 도서입니다."}, status=400)

    #이미 연장했는지 확인
    if borrow.is_extended:
        return JsonResponse({"error": "이미 1회 연장한 도서입니다."}, status=400)
        
    #연체되었는지 확인
    if borrow.due_date < date.today():
        return JsonResponse({"error": "연체된 도서는 연장할 수 없습니다."}, status=400)

    #(성공) 연장 처리: 7일 연장
    policy = Policy.load()
    new_due_date = borrow.due_date + timedelta(days=policy.max_extend_days)
    borrow.due_date = new_due_date
    borrow.is_extended = True # 연장 플래그를 True로 변경
    borrow.save()

    return JsonResponse({
        "message": "대여 기간이 연장되었습니다.",
        "new_due_date": new_due_date
    }, status=200)


# 도서 반납
@csrf_exempt
def return_book(request):
    if request.method != 'POST':
        return JsonResponse({"error": "POST 요청만 허용됩니다."}, status=405)

    if not request.user.is_authenticated:
        return JsonResponse({"error": "로그인이 필요합니다."}, status=401)

    try:
        data = json.loads(request.body)
        borrow_id = data['borrow_id'] # 반납할 대여 기록의 ID
        
        #트랜잭션 시작 (Borrow, Book, Member 테이블을 동시에 수정해야 하므로 트랜잭션으로 묶는다.)
        with transaction.atomic():
            borrow = Borrow.objects.select_related('book', 'member').get(borrow_id=borrow_id)
            
            #(보안) 본인의 대여 기록인지 확인
            if borrow.member != request.user:
                return JsonResponse({"error": "본인의 대여 기록만 반납할 수 있습니다."}, status=403)

            #이미 반납했는지 확인
            if borrow.return_date is not None:
                return JsonResponse({"error": "이미 반납 처리된 도서입니다."}, status=400)

            today = date.today()
            is_overdue = False

            #Borrow 테이블 업데이트 (반납일 기록)
            borrow.return_date = today
            borrow.save()

            #Book 테이블 업데이트 (책 상태를 "대여가능"으로 변경)
            book_to_return = borrow.book
            book_to_return.status = Book.Status.AVAILABLE #0
            book_to_return.save()

            #연체 여부 확인 및 처리
            if today > borrow.due_date:
                policy = Policy.load()
                is_overdue = True
                member = borrow.member
                member.status = "대여정지"
                member.overdue_end_date = today + timedelta(days=policy.overdue_penalty_days) #7일간 대여 정지
                member.save()

            return JsonResponse({
                "message": "도서 반납이 완료되었습니다.",
                "is_overdue": is_overdue # 연체 여부 반환
            }, status=200)

    except (KeyError, json.JSONDecodeError):
        return JsonResponse({"error": "borrow_id가 필요합니다."}, status=400)
    except Borrow.DoesNotExist:
        return JsonResponse({"error": "존재하지 않는 대여 기록입니다."}, status=404)
    except Exception as e:
        #트랜잭션 중 오류가 발생하면 모든 작업이 롤백
        return JsonResponse({"error": f"반납 처리 중 오류 발생: {str(e)}"}, status=500)
    
# 리뷰 작성
@csrf_exempt
def create_review(request):
    if request.method != 'POST':
        return JsonResponse({"error": "POST 요청만 허용됩니다."}, status=405)

    if not request.user.is_authenticated:
        return JsonResponse({"error": "로그인이 필요합니다."}, status=401)

    try:
        data = json.loads(request.body)
        isbn = data['isbn']
        rating = data['rating']
        content = data.get('content', "") # 내용은 선택 사항

        #리뷰할 BookInfo(책 정보)가 존재하는지 확인
        book_info = BookInfo.objects.get(isbn=isbn)

        #이미 이 책에 리뷰를 작성했는지 확인 (중복 방지)
        if Review.objects.filter(member=request.user, isbn=book_info).exists():
            return JsonResponse({"error": "이미 이 책에 대한 리뷰를 작성했습니다."}, status=400)

        #이 책을 대여한 적이 있는지 확인
        if not Borrow.objects.filter(member=request.user, book__isbn=book_info).exists():
            return JsonResponse({"error": "이 책을 대여한 사용자만 리뷰를 작성할 수 있습니다."}, status=403)

        # 4. 리뷰 생성
        #.save() 전에 .full_clean()을 호출하여 유효성 검사 실행 (이때 MinValueValidator(1), MaxValueValidator(5)가 작동)
        new_review = Review(
            member=request.user,
            isbn=book_info,
            rating=rating,
            content=content
        )

        new_review.full_clean()

        new_review.save()
        
        return JsonResponse({"message": "리뷰가 성공적으로 작성되었습니다.", "review_id": new_review.review_id}, status=201)

    except (KeyError, json.JSONDecodeError):
        return JsonResponse({"error": "isbn, rating, content가 필요합니다."}, status=400)
    except BookInfo.DoesNotExist:
        return JsonResponse({"error": "존재하지 않는 책(ISBN)입니다."}, status=404)
    
    except ValidationError as e:
        return JsonResponse({"error": e.message_dict}, status=400)
    
    except Exception as e:
        return JsonResponse({"error": f"리뷰 작성 중 오류 발생: {str(e)}"}, status=500)

#리뷰 읽기
def read_reviews(request, isbn): # URL로부터 isbn 값을 받음
    
    if request.method != 'GET':
        return JsonResponse({"error": "GET 요청만 허용됩니다."}, status=405)

    try:
        #이 ISBN을 가진 책이 실제로 존재하는지 확인
        book_info = BookInfo.objects.get(isbn=isbn)
    except BookInfo.DoesNotExist:
        return JsonResponse({"error": "존재하지 않는 책(ISBN)입니다."}, status=404)

    try:
        #(검색) 이 책(book_info)에 연결된 모든 리뷰를 찾음
        reviews_queryset = Review.objects.filter(isbn=book_info).order_by('-created_at') #최신순(-created_at)으로 정렬
        
        #QuerySet을 JSON으로 변환
        #.values()를 사용해 필요한 데이터만 딕셔너리 리스트로 변환
        #member__login_id: 리뷰의 member 필드를 통해 Member 모델의 login_id에 접근
        reviews_list = list(reviews_queryset.values(
            'review_id',
            'rating',
            'content',
            'created_at',
            'member__login_id' # 작성자를 표시
        ))
        
        return JsonResponse({'reviews': reviews_list}, status=200)

    except Exception as e:
        return JsonResponse({"error": f"리뷰를 불러오는 중 오류 발생: {str(e)}"}, status=500)
    

# 리뷰 수정
@csrf_exempt
def update_review(request, review_id): #URL에서 review_id를 받음
    if request.method != 'POST':
        return JsonResponse({"error": "POST 요청만 허용됩니다."}, status=405)

    if not request.user.is_authenticated:
        return JsonResponse({"error": "로그인이 필요합니다."}, status=401)

    try:
        #수정할 리뷰를 DB에서 찾음
        review = Review.objects.get(review_id=review_id)
    except Review.DoesNotExist:
        return JsonResponse({"error": "존재하지 않는 리뷰입니다."}, status=404)

    #리뷰 작성자(review.member)와 로그인한 사용자(request.user)가 같은지 확인
    if review.member != request.user:
        return JsonResponse({"error": "본인의 리뷰만 수정할 수 있습니다."}, status=403)

    try:
        data = json.loads(request.body)
        
        #수정할 내용만(선택적) 받아서 업데이트
        if 'rating' in data:
            review.rating = data['rating']
        if 'content' in data:
            review.content = data['content']

        #.save() 전에 .full_clean()을 호출
        review.full_clean()
        review.save()
        
        return JsonResponse({"message": "리뷰가 성공적으로 수정되었습니다."}, status=200)

    except (KeyError, json.JSONDecodeError):
        return JsonResponse({"error": "잘못된 요청 형식입니다."}, status=400)
    except ValidationError as e:
        return JsonResponse({"error": e.message_dict}, status=400)
    except Exception as e:
        return JsonResponse({"error": f"수정 중 오류 발생: {str(e)}"}, status=500)


# 리뷰 삭제
@csrf_exempt
def delete_review(request, review_id): #URL에서 review_id를 받음
    if request.method != 'POST':
        return JsonResponse({"error": "POST 요청만 허용됩니다."}, status=405)

    if not request.user.is_authenticated:
        return JsonResponse({"error": "로그인이 필요합니다."}, status=401)

    try:
        #삭제할 리뷰를 DB에서 찾음
        review = Review.objects.get(review_id=review_id)
    except Review.DoesNotExist:
        return JsonResponse({"error": "존재하지 않는 리뷰입니다."}, status=404)

    #리뷰 작성자(review.member)와 로그인한 사용자(request.user)가 같은지 확인
    if review.member != request.user:
        return JsonResponse({"error": "본인의 리뷰만 삭제할 수 있습니다."}, status=403)

    try:
        #리뷰 삭제
        review.delete()
        
        return JsonResponse({"message": "리뷰가 성공적으로 삭제되었습니다."}, status=200)

    except Exception as e:
        return JsonResponse({"error": f"삭제 중 오류 발생: {str(e)}"}, status=500)
    

    # **********************기능 추가************************
# id 중복 검사
@csrf_exempt
def check_id_duplicate(request):
    if request.method != 'POST':
        return JsonResponse({"error": "POST 요청만 허용됩니다."}, status=405)
    
    try:
        data = json.loads(request.body)
        member_id = data.get('member_id')
        
        if Member.objects.filter(login_id=member_id).exists():
            return JsonResponse({"status": "error", "message": "이미 존재하는 아이디입니다."}, status=200)
        else:
            return JsonResponse({"status": "success", "message": "사용 가능한 아이디입니다."}, status=200)
            
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

# email 중복 검사
@csrf_exempt
def check_email_duplicate(request):
    if request.method != 'POST':
        return JsonResponse({"error": "POST 요청만 허용됩니다."}, status=405)
    
    try:
        data = json.loads(request.body)
        email = data.get('email')
        
        if Member.objects.filter(email=email).exists():
            return JsonResponse({"status": "error", "message": "이미 존재하는 이메일입니다."}, status=200)
        else:
            return JsonResponse({"status": "success", "message": "사용 가능한 이메일입니다."}, status=200)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# 사용자의 상태 체크(대여 여부, 리뷰 여부)
@csrf_exempt
def check_user_book_status(request, isbn):
    """
    특정 도서에 대한 사용자의 상태(대여 여부, 리뷰 작성 여부)를 확인
    URL 예시: /api/books/<isbn>/status/
    """
    if request.method != 'GET':
        return JsonResponse({"error": "GET 요청만 허용됩니다."}, status=405)
    
    # 최종으로 로그인 확인
    if not request.user.is_authenticated:
        return JsonResponse({
            "is_authenticated": False,
            "has_borrowed": False,
            "my_review": None
        }, status=200)
    
    try:
        user = request.user
        # 1. 대여 기록 확인 (Borrow 테이블에서 해당 사용자와 ISBN으로 검색)
        # 빌린 기록이 있으면(과거 포함) 쓸 수 있게 설정
        has_borrowed = Borrow.objects.filter(member=user, book__isbn=isbn).exists()

        # 2. 내 리뷰 확인
        my_review = Review.objects.filter(member=user, isbn__isbn=isbn).first()
        
        review_data = None
        if my_review:
            review_data = {
                "review_id": my_review.review_id,
                "rating": my_review.rating,
                "content": my_review.content
            }

        return JsonResponse({
            "is_authenticated": True,
            "has_borrowed": has_borrowed,
            "my_review": review_data
        }, status=200)

    except Exception as e:
        return JsonResponse({"error": f"상태 확인 중 오류: {str(e)}"}, status=500)
    
    
#-----------------------관리자 기능-----------------------------------

#전체 회원 목록 조회 (검색 포함)
def admin_list_members(request):
    if request.method != 'GET':
        return JsonResponse({"error": "GET 요청만 허용됩니다."}, status=405)

    #관리자 권한 확인
    if not request.user.is_authenticated or not request.user.is_staff:
        return JsonResponse({"error": "관리자 권한이 필요합니다."}, status=403)

    try:
        #검색어(q) 가져오기 (예: /api/admin/members/?q=홍길동)
        query = request.GET.get('q', '')
        
        members = Member.objects.all().order_by('-date_joined') #가입일 역순

        if query:
            #이름, 아이디, 이메일, 전화번호 중 하나라도 포함되면 검색
            members = members.filter(
                Q(first_name__icontains=query) |
                Q(login_id__icontains=query) |
                Q(email__icontains=query) |
                Q(phone_number__icontains=query)
            )

        members_list = list(members.values(
            'id', 'login_id', 'first_name', 'email', 
            'phone_number', 'birth_date', 'status', 'date_joined', 'is_active'
        ))
        
        return JsonResponse({'members': members_list}, status=200)

    except Exception as e:
        return JsonResponse({"error": f"회원 목록 조회 중 오류: {str(e)}"}, status=500)


#특정 회원 상세 정보 조회
def admin_get_member(request, member_id):
    if request.method != 'GET':
        return JsonResponse({"error": "GET 요청만 허용됩니다."}, status=405)

    if not request.user.is_authenticated or not request.user.is_staff:
        return JsonResponse({"error": "관리자 권한이 필요합니다."}, status=403)
    
    try:
        member = Member.objects.get(id=member_id)
        
        return JsonResponse({
            'member_id': member.id,
            'login_id': member.login_id,
            'first_name': member.first_name,
            'email': member.email,
            'phone_number': member.phone_number,
            'birth_date': member.birth_date,
            'status': member.status,
            'overdue_end_date': member.overdue_end_date,
            'date_joined': member.date_joined,
            'is_active': member.is_active,
            'is_staff': member.is_staff
        }, status=200)

    except Member.DoesNotExist:
        return JsonResponse({"error": "존재하지 않는 회원입니다."}, status=404)
    
#관리자가 직접 회원 등록
@csrf_exempt
def admin_create_member(request):
    if request.method != 'POST':
        return JsonResponse({"error": "POST 요청만 허용됩니다."}, status=405)

    #관리자 권한 확인
    if not request.user.is_authenticated or not request.user.is_staff:
        return JsonResponse({"error": "관리자 권한이 필요합니다."}, status=403)

    try:

        print(request.body)
        data = json.loads(request.body)
        
        #필수 정보 추출
        login_id = data['login_id']
        password = data['password']
        first_name = data['first_name']
        email = data['email']
        birth_date = data['birth_date']
        phone_number = data['phone_number']
        
        #(선택) 관리자가 직접 상태를 지정하는 경우 (기본값: 정상)
        status = data.get('status', '정상')

        #비밀번호 암호화
        hashed_password = make_password(password)

        #회원 생성
        new_member = Member.objects.create(
            login_id=login_id,
            password=hashed_password,
            first_name=first_name,
            email=email,
            birth_date=birth_date,
            phone_number=phone_number,
            status=status
        )
        
        return JsonResponse({"message": "회원이 성공적으로 등록되었습니다.", "member_id": new_member.login_id}, status=201)

    except IntegrityError:
        return JsonResponse({"error": "이미 존재하는 아이디, 이메일 또는 전화번호입니다."}, status=400)
    except (KeyError, json.JSONDecodeError):
        return JsonResponse({"error": "필수 입력값이 누락되었습니다."}, status=400)
    except Exception as e:
        return JsonResponse({"error": f"회원 등록 중 오류: {str(e)}"}, status=500)

#회원 정보 및 상태 수정
@csrf_exempt
def admin_update_member(request, member_id):
    if request.method != 'POST':
        return JsonResponse({"error": "POST 요청만 허용됩니다."}, status=405)

    if not request.user.is_authenticated or not request.user.is_staff:
        return JsonResponse({"error": "관리자 권한이 필요합니다."}, status=403)

    try:
        member = Member.objects.get(id=member_id)
        data = json.loads(request.body)

        # 수정 가능한 필드들 (값이 있는 경우에만 업데이트)
        if 'first_name' in data: member.first_name = data['first_name']
        if 'email' in data: member.email = data['email']
        if 'phone_number' in data: member.phone_number = data['phone_number']
        if 'birth_date' in data: member.birth_date = data['birth_date']
        
        #관리자 기능: 상태 변경 (정상, 대여정지, 탈퇴 등)
        if 'status' in data: 
            member.status = data['status']
            
            #상태가 '정상'으로 돌아오면 연체 종료일 초기화
            if member.status == '정상':
                member.overdue_end_date = None
            #상태가 '탈퇴'라면 비활성화 처리
            if member.status == '탈퇴':
                member.is_active = False
            elif member.status in ['정상', '대여정지']:
                member.is_active = True #다시 복구할 경우

        #관리자 기능: 연체 종료일 수동 설정
        if 'overdue_end_date' in data:
            member.overdue_end_date = data['overdue_end_date'] # null 또는 'YYYY-MM-DD'

        member.save()

        return JsonResponse({"message": "회원 정보가 수정되었습니다."}, status=200)

    except Member.DoesNotExist:
        return JsonResponse({"error": "존재하지 않는 회원입니다."}, status=404)
    except Exception as e:
        return JsonResponse({"error": f"회원 수정 중 오류: {str(e)}"}, status=500)


#회원 삭제 (실제 삭제 대신 탈퇴 처리)
@csrf_exempt
def admin_delete_member(request, member_id):
    if request.method != 'POST':
        return JsonResponse({"error": "POST 요청만 허용됩니다."}, status=405)

    if not request.user.is_authenticated or not request.user.is_staff:
        return JsonResponse({"error": "관리자 권한이 필요합니다."}, status=403)

    try:
        member = Member.objects.get(id=member_id)
        
        #비활성화 처리
        member.is_active = False
        member.status = "탈퇴"
        member.save()

        return JsonResponse({"message": "회원이 성공적으로 탈퇴(비활성화) 처리되었습니다."}, status=200)

    except Member.DoesNotExist:
        return JsonResponse({"error": "존재하지 않는 회원입니다."}, status=404)
    
#특정 회원의 대여/반납 기록 조회
def admin_member_borrows(request, member_id):
    if request.method != 'GET':
        return JsonResponse({"error": "GET 요청만 허용됩니다."}, status=405)

    #관리자 권한 확인
    if not request.user.is_authenticated or not request.user.is_staff:
        return JsonResponse({"error": "관리자 권한이 필요합니다."}, status=403)
    try:
        #조회 대상 회원이 존재하는지 확인
        target_member = Member.objects.get(id=member_id)

        #해당 회원의 대여/반납 기록 조회 (최신순 정렬)
        borrows_queryset = Borrow.objects.filter(member=target_member).select_related(
            'book', 'book__isbn'
        ).order_by('-borrow_date')

        borrows_list = list(borrows_queryset.values(
            'borrow_id',
            'borrow_date',
            'due_date',
            'return_date',
            'is_extended',
            'book__book_manage_id', # 도서 관리 번호
            'book__isbn__title',    # 책 제목
            'book__isbn__isbn'      # ISBN
        ))

        return JsonResponse({
            "member_name": target_member.first_name,
            "borrows": borrows_list
        }, status=200)

    except Member.DoesNotExist:
        return JsonResponse({"error": "존재하지 않는 회원입니다."}, status=404)
    except Exception as e:
        return JsonResponse({"error": f"대여 기록 조회 중 오류: {str(e)}"}, status=500)
    
@csrf_exempt
def admin_borrow_book(request):
    if request.method != 'POST':
        return JsonResponse({"error": "POST 요청만 허용됩니다."}, status=405)

    # 관리자 권한 확인
    if not request.user.is_authenticated or not request.user.is_staff:
        return JsonResponse({"error": "관리자 권한이 필요합니다."}, status=403)

    try:
        data = json.loads(request.body)
        target_member_id = data['member_id'] 
        isbn_list = data['isbns']
        
        target_member = Member.objects.get(id=target_member_id)

        # [수정] .name -> .first_name 으로 변경
        if target_member.status == "대여정지":
             return JsonResponse({
                "error": f"해당 회원({target_member.first_name})은 '대여정지' 상태입니다. 회원 정보 수정에서 상태를 변경하세요."
            }, status=400)

    except (KeyError, json.JSONDecodeError):
        return JsonResponse({"error": "member_id와 isbns가 필요합니다."}, status=400)
    except Member.DoesNotExist:
        return JsonResponse({"error": "존재하지 않는 회원입니다."}, status=404)

    successful_borrows = []
    failed_borrows = []
    today = date.today()
    policy = Policy.load()
    due_date = today + timedelta(days=policy.default_due_days)

    try:
        with transaction.atomic():
            for isbn in isbn_list:
                # ISBN 검색
                available_copy = Book.objects.select_for_update().filter(
                    isbn__isbn=isbn, 
                    status=Book.Status.AVAILABLE
                ).first()

                if available_copy:
                    Borrow.objects.create(
                        member=target_member, 
                        book=available_copy, 
                        borrow_date=today,
                        due_date=due_date
                    )
                    available_copy.status = Book.Status.BORROWED
                    available_copy.save()
                    successful_borrows.append(isbn)
                else:
                    failed_borrows.append(isbn)
    
    except Exception as e:
        return JsonResponse({"error": f"관리자 대여 처리 중 오류: {str(e)}"}, status=500)

    # [수정] .name -> .first_name 으로 변경
    return JsonResponse({
        "message": f"{target_member.first_name}님에 대한 대여 처리가 완료되었습니다.",
        "successful_isbns": successful_borrows,
        "failed_isbns": failed_borrows
    }, status=200)

@csrf_exempt
def admin_return_book(request):
    if request.method != 'POST':
        return JsonResponse({"error": "POST 요청만 허용됩니다."}, status=405)

    if not request.user.is_authenticated or not request.user.is_staff:
        return JsonResponse({"error": "관리자 권한이 필요합니다."}, status=403)

    try:
        data = json.loads(request.body)
        borrow_id = data['borrow_id'] 
        
        with transaction.atomic():
            loan = Borrow.objects.select_related('book', 'member').get(pk=borrow_id)
            
            if loan.return_date is not None:
                return JsonResponse({"error": "이미 반납 처리된 도서입니다."}, status=400)

            today = date.today()
            is_overdue = False

            loan.return_date = today
            loan.save()

            book_to_return = loan.book
            book_to_return.status = Book.Status.AVAILABLE
            book_to_return.save()

            if today > loan.due_date:
                is_overdue = True
                member = loan.member
                member.status = "대여정지"
                policy = Policy.load()
                member.overdue_end_date = today + timedelta(days=policy.overdue_penalty_days)
                member.save()

            # [수정] loan.member.name -> loan.member.first_name 으로 변경
            return JsonResponse({
                "message": "관리자 권한으로 반납 처리가 완료되었습니다.",
                "returned_member": loan.member.first_name,
                "is_overdue": is_overdue
            }, status=200)

    except Borrow.DoesNotExist:
        return JsonResponse({"error": "존재하지 않는 대여 기록입니다."}, status=404)
    except Exception as e:
        return JsonResponse({"error": f"반납 처리 중 오류: {str(e)}"}, status=500)
    
#새 도서 등록
@csrf_exempt
def admin_create_book(request):
    if request.method != 'POST':
        return JsonResponse({"error": "POST 요청만 허용됩니다."}, status=405)

    if not request.user.is_authenticated or not request.user.is_staff:
        return JsonResponse({"error": "관리자 권한이 필요합니다."}, status=403)

    try:
        data = json.loads(request.body)
        
        #필수 정보
        isbn = data['isbn']
        title = data['title']
        category_id = data['category_id']
        publisher_name = data['publisher_name'] #출판사 이름 (없으면 생성)
        
        #선택 정보
        author = data.get('author', "")
        copy_count = int(data.get('copy_count', 1)) #실물 책 생성 개수 (기본 1권)
        image_url = data.get('image_url')
        #카테고리 확인
        try:
            category = Category.objects.get(category_id=category_id)
        except Category.DoesNotExist:
            return JsonResponse({"error": "존재하지 않는 카테고리 ID입니다."}, status=400)

        #출판사 확인 (없으면 생성 - get_or_create)
        #import_publisher 스크립트 때처럼 publisher_name을 기준으로 조회
        publisher, _ = Publisher.objects.get_or_create(
            publisher_name=publisher_name
        )

        #도서 정보(BookInfo) 생성(이미 존재하는 ISBN이면 에러 반환)
        if BookInfo.objects.filter(isbn=isbn).exists():
            return JsonResponse({"error": "이미 등록된 ISBN입니다."}, status=400)

        book_info = BookInfo.objects.create(
            isbn=isbn,
            title=title,
            author=author,
            category=category,
            publisher=publisher,
            image_url=image_url
        )

        #실물 책(Book) 생성 (수량만큼 반복)
        created_copies = []
        for _ in range(copy_count):
            new_copy = Book.objects.create(
                isbn=book_info,
                status=Book.Status.AVAILABLE
            )
            created_copies.append(new_copy.book_manage_id)

        return JsonResponse({
            "message": f"도서 '{title}' 등록 및 {copy_count}권 입고 완료",
            "isbn": book_info.isbn,
            "created_book_ids": created_copies
        }, status=201)

    except (KeyError, json.JSONDecodeError):
        return JsonResponse({"error": "필수 정보(isbn, title, category_id, publisher_name)가 누락되었습니다."}, status=400)
    except Exception as e:
        return JsonResponse({"error": f"도서 등록 중 오류: {str(e)}"}, status=500)


#도서 정보 수정
@csrf_exempt
def admin_update_book(request, isbn):
    if request.method != 'POST':
        return JsonResponse({"error": "POST 요청만 허용됩니다."}, status=405)

    if not request.user.is_authenticated or not request.user.is_staff:
        return JsonResponse({"error": "관리자 권한이 필요합니다."}, status=403)

    try:
        book_info = BookInfo.objects.get(isbn=isbn)
        data = json.loads(request.body)

        if 'title' in data: book_info.title = data['title']
        if 'author' in data: book_info.author = data['author']
        # 추가 -> 이미지 URL 변경
        if 'image_url' in data: book_info.image_url = data['image_url']
        
        #카테고리 변경
        if 'category_id' in data:
            try:
                category = Category.objects.get(category_id=data['category_id'])
                book_info.category = category
            except Category.DoesNotExist:
                return JsonResponse({"error": "존재하지 않는 카테고리 ID입니다."}, status=400)

        #출판사 변경 (이름으로 찾거나 생성)
        if 'publisher_name' in data:
            publisher, _ = Publisher.objects.get_or_create(publisher_name=data['publisher_name'])
            book_info.publisher = publisher

        book_info.save()
        return JsonResponse({"message": "도서 정보가 수정되었습니다."}, status=200)

    except BookInfo.DoesNotExist:
        return JsonResponse({"error": "존재하지 않는 도서(ISBN)입니다."}, status=404)
    except Exception as e:
        return JsonResponse({"error": f"수정 중 오류: {str(e)}"}, status=500)


#도서 삭제
@csrf_exempt
def admin_delete_book(request, isbn):
    if request.method != 'POST':
        return JsonResponse({"error": "POST 요청만 허용됩니다."}, status=405)

    if not request.user.is_authenticated or not request.user.is_staff:
        return JsonResponse({"error": "관리자 권한이 필요합니다."}, status=403)

    try:
        book_info = BookInfo.objects.get(isbn=isbn)
        
        #BookInfo를 삭제하면 models.py의 on_delete=models.CASCADE 설정에 의해 연결된 실물 책(Book)과 리뷰(Review)도 모두 함께 삭제
        book_info.delete()
        
        return JsonResponse({"message": "도서 및 관련 데이터가 모두 삭제되었습니다."}, status=200)

    except BookInfo.DoesNotExist:
        return JsonResponse({"error": "존재하지 않는 도서(ISBN)입니다."}, status=404)


#개별 실물 책 상태 수정
@csrf_exempt
def admin_update_book_copy(request, book_manage_id):
    if request.method != 'POST':
        return JsonResponse({"error": "POST 요청만 허용됩니다."}, status=405)

    if not request.user.is_authenticated or not request.user.is_staff:
        return JsonResponse({"error": "관리자 권한이 필요합니다."}, status=403)

    try:
        book_copy = Book.objects.get(book_manage_id=book_manage_id)
        data = json.loads(request.body)
        
        if 'status' in data:
            raw_input = str(data['status']) #입력값을 무조건 문자열로 변환 ("0", 0, "대여 가능" 모두 대응)
            
            #공백 제거 ("대여 가능" -> "대여가능", " 0 " -> "0")
            clean_input = raw_input.replace(" ", "")

            #매핑 테이블 정의 (입력 가능한 경우의 수 -> 정확한 정수형 코드)
            status_map = {
                '대여가능': Book.Status.AVAILABLE, #0
                '0': Book.Status.AVAILABLE,       #0
                
                '대여중': Book.Status.BORROWED,   #1
                '1': Book.Status.BORROWED,        #1
                
                '대여불가': Book.Status.UNAVAILABLE, #2
                '2': Book.Status.UNAVAILABLE,        #2
                '분실': Book.Status.UNAVAILABLE,     #'분실'도 '대여불가'로 처리
                '폐기': Book.Status.UNAVAILABLE,     #'폐기'도 '대여불가'로 처리
            }

            if clean_input in status_map:
                book_copy.status = status_map[clean_input]
            else:
                return JsonResponse({
                    "error": f"잘못된 상태 값입니다: '{data['status']}'. (허용: 대여가능/0, 대여중/1, 대여불가/2)"
                }, status=400)

            book_copy.save()
            
        return JsonResponse({
            "message": f"도서(ID:{book_manage_id}) 상태가 '{book_copy.get_status_display()}'({book_copy.status})로 변경되었습니다."
        }, status=200)

    except Book.DoesNotExist:
        return JsonResponse({"error": "존재하지 않는 실물 도서입니다."}, status=404)
    except Exception as e:
        return JsonResponse({"error": f"상태 수정 중 오류: {str(e)}"}, status=500)

# ************** 추가 ****************
# 특정 도서(ISBN)의 실물 책 목록 조회 (관리자용)
def admin_get_book_copies(request, isbn):
    if request.method != 'GET':
        return JsonResponse({"error": "GET 요청만 허용됩니다."}, status=405)

    if not request.user.is_authenticated or not request.user.is_staff:
        return JsonResponse({"error": "관리자 권한이 필요합니다."}, status=403)

    try:
        # 해당 ISBN을 가진 모든 실물 책 조회
        copies = Book.objects.filter(isbn=isbn).order_by('book_manage_id')
        
        copies_list = []
        for copy in copies:
            copies_list.append({
                'book_manage_id': copy.book_manage_id,
                'status': copy.status,
                'status_display': copy.get_status_display() # "대여가능", "대여중" 등 텍스트
            })
            
        return JsonResponse({'copies': copies_list}, status=200)

    except Exception as e:
        return JsonResponse({"error": f"목록 조회 중 오류: {str(e)}"}, status=500)
    
# ************** 추가 ****************
# 기존 도서에 실물 책(Copy) 추가 입고
@csrf_exempt
def admin_add_book_copies(request, isbn):
    if request.method != 'POST':
        return JsonResponse({"error": "POST 요청만 허용됩니다."}, status=405)

    if not request.user.is_authenticated or not request.user.is_staff:
        return JsonResponse({"error": "관리자 권한이 필요합니다."}, status=403)

    try:
        book_info = BookInfo.objects.get(isbn=isbn)
        data = json.loads(request.body)
        
        # 추가할 수량 (기본 1권)
        amount = int(data.get('amount', 1))
        
        if amount < 1:
             return JsonResponse({"error": "1권 이상 입력해야 합니다."}, status=400)

        created_ids = []
        for _ in range(amount):
            new_copy = Book.objects.create(
                isbn=book_info,
                status=Book.Status.AVAILABLE # 기본 대여 가능 상태로 생성
            )
            created_ids.append(new_copy.book_manage_id)

        return JsonResponse({
            "message": f"{amount}권이 추가 입고되었습니다.",
            "added_ids": created_ids
        }, status=201)

    except BookInfo.DoesNotExist:
        return JsonResponse({"error": "존재하지 않는 도서(ISBN)입니다."}, status=404)
    except (ValueError, TypeError):
         return JsonResponse({"error": "수량은 숫자여야 합니다."}, status=400)
    except Exception as e:
        return JsonResponse({"error": f"입고 처리 중 오류: {str(e)}"}, status=500)


#카테고리 관리 (조회 및 추가)
@csrf_exempt
def admin_categories(request):
    #권한 확인
    if not request.user.is_authenticated or not request.user.is_staff:
        return JsonResponse({"error": "관리자 권한이 필요합니다."}, status=403)

    #GET: 전체 카테고리 목록 조회
    if request.method == 'GET':
        categories = Category.objects.all().values('category_id', 'category_name')
        return JsonResponse({'categories': list(categories)}, status=200)

    #POST: 새 카테고리 추가
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            #category_id가 AutoField가 아니어서 수동으로 입력받아야 함
            cat_id = data.get('category_id')
            cat_name = data['category_name']

            if cat_id:
                category = Category.objects.create(category_id=cat_id, category_name=cat_name)
            else:
                #ID 입력 안하면 IntegerField이기에 오류
                return JsonResponse({"error": "category_id가 필요합니다."}, status=400)
                
            return JsonResponse({"message": "카테고리가 추가되었습니다."}, status=201)

        except IntegrityError:
            return JsonResponse({"error": "이미 존재하는 카테고리 ID 또는 이름입니다."}, status=400)
        except (KeyError, json.JSONDecodeError):
            return JsonResponse({"error": "category_id와 category_name이 필요합니다."}, status=400)
            
    else:
        return JsonResponse({"error": "허용되지 않는 요청입니다."}, status=405)


#카테고리 삭제
@csrf_exempt
def admin_delete_category(request, category_id):
    if request.method != 'POST':
        return JsonResponse({"error": "POST 요청만 허용됩니다."}, status=405)

    if not request.user.is_authenticated or not request.user.is_staff:
        return JsonResponse({"error": "관리자 권한이 필요합니다."}, status=403)

    try:
        category = Category.objects.get(category_id=category_id)
        category.delete()
        return JsonResponse({"message": "카테고리가 삭제되었습니다."}, status=200)

    except Category.DoesNotExist:
        return JsonResponse({"error": "존재하지 않는 카테고리입니다."}, status=404)
        
    except ProtectedError:
        return JsonResponse({
            "error": "이 카테고리에 등록된 도서가 있어 삭제할 수 없습니다. 해당 도서들의 카테고리를 먼저 변경해주세요."
        }, status=400)
    
#출판사 목록 조회 (검색 기능 포함)
def admin_list_publishers(request):
    if request.method != 'GET':
        return JsonResponse({"error": "GET 요청만 허용됩니다."}, status=405)

    #관리자 권한 확인
    if not request.user.is_authenticated or not request.user.is_staff:
        return JsonResponse({"error": "관리자 권한이 필요합니다."}, status=403)

    try:
        #검색어(q) 가져오기 (예: /api/admin/publishers/?q=민음사)
        query = request.GET.get('q', '')
        
        publishers = Publisher.objects.all().order_by('publisher_id')

        if query:
            #출판사명 또는 전화번호로 검색
            publishers = publishers.filter(
                Q(publisher_name__icontains=query) |
                Q(phone_number__icontains=query)
            )

        #결과 JSON 변환
        publishers_list = list(publishers.values(
            'publisher_id', 'publisher_name', 'phone_number'
        ))
        
        return JsonResponse({'publishers': publishers_list}, status=200)

    except Exception as e:
        return JsonResponse({"error": f"출판사 목록 조회 중 오류: {str(e)}"}, status=500)


#새 출판사 등록
@csrf_exempt
def admin_create_publisher(request):
    if request.method != 'POST':
        return JsonResponse({"error": "POST 요청만 허용됩니다."}, status=405)

    if not request.user.is_authenticated or not request.user.is_staff:
        return JsonResponse({"error": "관리자 권한이 필요합니다."}, status=403)

    try:
        data = json.loads(request.body)
        
        publisher_name = data['publisher_name']
        phone_number = data.get('phone_number', "") #연락처는 not null이 아니라서 선택 사항

        #출판사 생성
        new_publisher = Publisher.objects.create(
            publisher_name=publisher_name,
            phone_number=phone_number
        )
        
        return JsonResponse({
            "message": "출판사가 성공적으로 등록되었습니다.",
            "publisher_id": new_publisher.publisher_id
        }, status=201)

    except IntegrityError:
        #publisher_name은 unique=True 이므로 중복 시 에러 발생
        return JsonResponse({"error": "이미 존재하는 출판사 이름입니다."}, status=400)
    except (KeyError, json.JSONDecodeError):
        return JsonResponse({"error": "publisher_name이 필요합니다."}, status=400)
    except Exception as e:
        return JsonResponse({"error": f"등록 중 오류 발생: {str(e)}"}, status=500)


#출판사 정보 수정
@csrf_exempt
def admin_update_publisher(request, publisher_id):
    if request.method != 'POST':
        return JsonResponse({"error": "POST 요청만 허용됩니다."}, status=405)

    if not request.user.is_authenticated or not request.user.is_staff:
        return JsonResponse({"error": "관리자 권한이 필요합니다."}, status=403)

    try:
        publisher = Publisher.objects.get(publisher_id=publisher_id)
        data = json.loads(request.body)

        #이름 변경
        if 'publisher_name' in data:
            new_name = data['publisher_name']
            #다른 출판사 중에 같은 이름이 있는지 확인
            if Publisher.objects.filter(publisher_name=new_name).exclude(pk=publisher_id).exists():
                 return JsonResponse({"error": "이미 존재하는 출판사 이름입니다."}, status=400)
            publisher.publisher_name = new_name

        #연락처 변경
        if 'phone_number' in data:
            publisher.phone_number = data['phone_number']

        publisher.save()

        return JsonResponse({"message": "출판사 정보가 수정되었습니다."}, status=200)

    except Publisher.DoesNotExist:
        return JsonResponse({"error": "존재하지 않는 출판사입니다."}, status=404)
    except Exception as e:
        return JsonResponse({"error": f"수정 중 오류 발생: {str(e)}"}, status=500)


#출판사 삭제
@csrf_exempt
def admin_delete_publisher(request, publisher_id):
    if request.method != 'POST':
        return JsonResponse({"error": "POST 요청만 허용됩니다."}, status=405)

    if not request.user.is_authenticated or not request.user.is_staff:
        return JsonResponse({"error": "관리자 권한이 필요합니다."}, status=403)

    try:
        publisher = Publisher.objects.get(publisher_id=publisher_id)
        publisher.delete()
        return JsonResponse({"message": "출판사가 삭제되었습니다."}, status=200)

    except Publisher.DoesNotExist:
        return JsonResponse({"error": "존재하지 않는 출판사입니다."}, status=404)

    except ProtectedError:
        return JsonResponse({
            "error": "이 출판사에 등록된 도서가 있어 삭제할 수 없습니다. 해당 도서들의 출판사 정보를 먼저 변경해주세요."
        }, status=400)
    
# [추가] 관리자용 전체 리뷰 목록 조회 (단순 조회)
def admin_list_reviews(request):
    if request.method != 'GET':
        return JsonResponse({"error": "GET 요청만 허용됩니다."}, status=405)

    if not request.user.is_authenticated or not request.user.is_staff:
        return JsonResponse({"error": "관리자 권한이 필요합니다."}, status=403)

    try:
        # 검색어(q) 처리만 남겨둠
        query = request.GET.get('q', '')
        
        # 기본적으로 최신순으로 가져오기 (DB에서 가져올 때 순서)
        reviews = Review.objects.select_related('member', 'isbn').order_by('-created_at')

        if query:
            reviews = reviews.filter(
                Q(content__icontains=query) |
                Q(member__login_id__icontains=query) |
                Q(isbn__title__icontains=query)
            )

        reviews_list = list(reviews.values(
            'review_id',
            'rating',
            'content',
            'created_at',
            'member__login_id',
            'isbn__title',
            'isbn__isbn'
        ))

        return JsonResponse({'reviews': reviews_list}, status=200)

    except Exception as e:
        return JsonResponse({"error": f"리뷰 목록 조회 중 오류: {str(e)}"}, status=500)

#리뷰 삭제
@csrf_exempt
def admin_delete_review(request, review_id):
    if request.method != 'POST':
        return JsonResponse({"error": "POST 요청만 허용됩니다."}, status=405)

    if not request.user.is_authenticated or not request.user.is_staff:
        return JsonResponse({"error": "관리자 권한이 필요합니다."}, status=403)

    try:
        review = Review.objects.get(review_id=review_id)
        review.delete()
        
        return JsonResponse({"message": "관리자 권한으로 리뷰가 삭제되었습니다."}, status=200)

    except Review.DoesNotExist:
        return JsonResponse({"error": "존재하지 않는 리뷰입니다."}, status=404)
    except Exception as e:
        return JsonResponse({"error": f"리뷰 삭제 중 오류 발생: {str(e)}"}, status=500)
    
#정책 조회 및 수정
@csrf_exempt
def admin_policy(request):
    if not request.user.is_authenticated or not request.user.is_staff:
        return JsonResponse({"error": "관리자 권한이 필요합니다."}, status=403)

    #현재 정책 조회
    policy = Policy.load()

    if request.method == 'GET':
        return JsonResponse({
            "max_borrow_count": policy.max_borrow_count,
            "default_due_days": policy.default_due_days,
            "max_extend_days": policy.max_extend_days,
            "overdue_penalty_days": policy.overdue_penalty_days
        }, status=200)

    #정책 수정
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            if 'max_borrow_count' in data: 
                policy.max_borrow_count = int(data['max_borrow_count'])
            if 'default_due_days' in data: 
                policy.default_due_days = int(data['default_due_days'])
            if 'max_extend_days' in data: 
                policy.max_extend_days = int(data['max_extend_days'])
            if 'overdue_penalty_days' in data: 
                policy.overdue_penalty_days = int(data['overdue_penalty_days'])
            
            policy.full_clean()
            policy.save()
            
            return JsonResponse({"message": "운영 정책이 수정되었습니다."}, status=200)
            
        except (ValueError, ValidationError) as e:
             return JsonResponse({"error": "잘못된 입력값입니다. (숫자만 가능)"}, status=400)
        except json.JSONDecodeError:
            return JsonResponse({"error": "잘못된 요청 형식입니다."}, status=400)
    
    else:
        return JsonResponse({"error": "허용되지 않는 요청입니다."}, status=405)
    
@csrf_exempt
def login_check(request):
    if request.method != 'GET':
        return JsonResponse({"error": "GET 요청만 허용됩니다."}, status=405)

    if request.user.is_authenticated:
        return JsonResponse({
            "is_authenticated": True,
            "login_id": request.user.login_id,
            "name": request.user.first_name
        }, status=200)
    else:
        return JsonResponse({"is_authenticated": False}, status=200)
