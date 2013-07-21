# -*- coding: utf-8 -*-

from django.template import Context, loader
from yighub.models import User, Board, Intro, Entry, Comment, File, Letter, Memo, UserForm, BoardForm, IntroForm, EntryForm, LetterForm
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import render_to_response, get_object_or_404, render, redirect
from django.template import RequestContext
from django.core.urlresolvers import reverse
from django.contrib import messages
import mimetypes
import datetime
from django.utils import timezone
from django.contrib.auth import hashers

def page(board_number, current_page): # board_number가 0이면 최신글 목록
    
    current_page = int(current_page)
    page_size = 20
    no = (current_page - 1) * page_size # 그 앞 페이지 마지막 글까지 개수

    # 총 글 수와 entry list 구하기
    if board_number != 0:
        board = Board.objects.get(pk = board_number)
        count_entry = board.count_entry #Entry.objects.filter(board = ... ).count()
        entry_list = Entry.objects.filter(board = board).order_by('-arrangement')[no : (no + page_size)]
    else:
        count_entry = Entry.objects.count()
        entry_list = Entry.objects.all().order_by('-arrangement')[no : (no + page_size)] # filter(board = board_number)

    # 첫 페이지와 끝 페이지 설정
    first_page = 1
    last_page = (count_entry - 1)/page_size + 1

    # 페이지 리스트 만들기
#    real_list = []
    for e in entry_list:
        e.range = range(e.depth)
        """
        if e.depth:
            try:
                p = Entry.objects.get(pk = e.parent)
            except Entry.DoesNotExist:
                real_list.append("원본 글이 삭제되었습니다.")
            else:
                if p.board.pk != board_number:
                    real_list.append("원본 글이 이동되었습니다.")
                else:
                    pass
        real_list.append(e) 
        """
    if current_page < 5:
        start_page = 1
    else:
        start_page = current_page - 4

    if current_page > last_page - 5:
        end_page = last_page
    else:
        end_page = current_page + 4

    page_list = range(start_page, end_page + 1)

    # 이전 페이지, 다음 페이지 설정
    prev_page = current_page - 1
    next_page = current_page + 1

    # 맨 첫 페이지나 맨 끝 페이지일 때 고려
    if current_page == last_page:
        next_page = 0
        last_page = 0
    if current_page == first_page:
        prev_page = 0
        first_page = 0

    return {'entry_list' : entry_list,
            'current_page' : current_page,
            'page_list' : page_list,
            'first_page' : first_page,
            'last_page' : last_page,
            'prev_page' : prev_page,
            'next_page' : next_page,
            }

def is_member(request):
    try:
        u = request.session['user_id']
        user = User.objects.get(user_id = u) 
    except KeyError:
        return False, redirect('yighub:login')
    except User.DoesNotExist: # 세션에는 남아있지만 데이터베이스에는 없는 경우. 회원탈퇴이거나 다른 app을 쓰다 접근.
        return False, redirect('yighub:logout',)
    
    if user.level == 'non':
        messages.error(request, '접근 권한이 없습니다.')
        return False, render(request, 'yighub/error.html', )
    else:
        return True, None # indexing을 위해 

def home(request, current_page = 1):
    if 'user_id' not in request.session:
        return render(request, 'yighub/home_for_visitor.html')
    else:
        u = request.session['user_id']
    try:
        user = User.objects.get(user_id = u)
    except User.DoesNotExist:
        return redirect(reverse('yighub:logout'))

    # 홈페이지를 열 때마다 마지막 방문날짜를 업데이트한다.
    user.last_login = timezone.now()
    
    if user.level == 'not':
        return render(request, 'yighub/home_for_visitor.html')

    # 최신글 목록 가져오기
    news = Entry.objects.all().order_by('-arrangement')[0:10]

    current_page = int(current_page)
    page_size = 10
    no = (current_page - 1) * page_size

    # 총 글 수와 entry list 구하기
    count_entry = Memo.objects.count()
    entry_list = Memo.objects.all().order_by('-pk')[no : (no + page_size)] # filter(board = board_number)

    # 첫 페이지와 끝 페이지 설정
    first_page = 1
    last_page = (count_entry - 1)/page_size + 1
    
    # 페이지 리스트 만들기
    if current_page < 5:
        start_page = 1
    else:
        start_page = current_page - 4

    if current_page > last_page - 5:
        end_page = last_page
    else:
        end_page = current_page + 4
    
    page_list = range(start_page, end_page + 1)

    # 이전 페이지, 다음 페이지 설정
    prev_page = current_page - 1
    next_page = current_page + 1
    
    # 맨 첫 페이지나 맨 끝 페이지일 때 고려
    if current_page == last_page:
        next_page = 0
        last_page = 0
    if current_page == first_page:
        prev_page = 0
        first_page = 0
    
    # memo 페이지 dictionary 만들기
    m = {'entry_list' : entry_list,
            'current_page' : current_page,
            'page_list' : page_list,
            'first_page' : first_page,
            'last_page' : last_page,
            'prev_page' : prev_page,
            'next_page' : next_page,
           }

    return render(request, 'yighub/home_for_member.html', # 아직까지는 페이지 넘기기 지원하지 않음.
                                  {'user' : user,
                                   'news' : news,
                                   'memos' : m,
                                   },   
                                  ) 

def board(request, board_number, current_page = 1):    # url : yig.in/yighub/board/1/page/3

    # 권한 검사
    permission = is_member(request)
    if permission[0] == False:
        return permission[1] 

    board_number = int(board_number)

    p = page(board_number, current_page)
    if board_number:
        b = Board.objects.get(pk = board_number)
    else:
        class b:
            pass
        b.name = '최신글 목록'

    if b.name == '최신글 목록':
        return render(request, 'yighub/news.html', {'user' : request.session['user'], 'board' : b, 'page' : p, })
    if b.name == 'Board':
        return render(request, 'yighub/board.html', {'user' : request.session['user'], 'board' : b, 'page' : p, })
    if b.name == 'Notice':
        return render(request, 'yighub/notice.html', {'user' : request.session['user'], 'board' : b, 'page' : p, })
    if b.name == 'Company Analysis':
        return render(request, 'yighub/company analysis.html', {'user' : request.session['user'], 'board' : b, 'page' : p, })
    if b.name == 'Portfolio':
        return render(request, 'yighub/portfolio.html', {'user' : request.session['user'], 'board' : b, 'page' : p, })
    if b.name == 'Column':
        return render(request, 'yighub/column.html', {'user' : request.session['user'], 'board' : b, 'page' : p, })
    else:
        return render(request, 'yighub/taskforce.html', {'user' : request.session['user'], 'board' : b, 'page' : p, })

def create_board(request):
    if request.method == 'POST':
        form = BoardForm(request.POST)
        if form.is_valid():

            form.save()

            return redirect('yighub:home', )
    else:
        form = BoardForm()

    return render(request, 'yighub/create_board.html', {'form' : form})

def edit_board(request):
    pass # 여기서 archive로 넘기기도 처리. 삭제는 일단 구현 안함. 게시글이 하나도 없을 때만 가능.

def read(request, entry_id):
    
    # 권한 검사
    permission = is_member(request)
    if permission[0] == False:
        return permission[1]

    try:
        e = Entry.objects.get(pk = entry_id) 
    except Entry.DoesNotExist:
        raise Http404
    
    e.count_view += 1
    e.save()

    u = request.session['user']
    recommendations = e.recommendation.all()
    files = e.files.all() #File.objects.filter(entry = e)
    comments = e.comment_set.all()

    return render(request, 'yighub/read.html',
      {'user' : u,
      'entry' : e,
      'files' : files,
      'recommendations' : recommendations,
      'comments' : comments,
      },
      )

def create(request, board_number = 0):
    if request.method == 'POST':
        form = EntryForm(request.POST)
        if form.is_valid():

            files = request.FILES.getlist('files')
            
            # arrangement 할당
            try:
                newest_entry = Entry.objects.order_by('-arrangement')[0] # largest board_number
            except IndexError:
                arrangement = 1000
            else:
                arrangement = (newest_entry.arrangement/1000 + 1) * 1000

            # 글을 저장한다.
            e = form.save(commit = False)
            e.creator = request.session['user']
            e.time_last_modified = timezone.now()
            e.arrangement = arrangement
            e.save()

            # 여러 파일들을 저장한다.
            for file in files:
                f = File(entry = e, name = file.name, file = file)
                f.save()
            
            # 게시판 정보를 업데이트한다.
            b = Board.objects.get(pk = request.POST['board'])
            b.count_entry += 1
            b.newest_entry = e.id
            b.newest_time = e.time_last_modified
            b.save()

            return redirect('yighub:home', )
    else:
        try:
            b = Board.objects.get(pk = board_number)
        except Board.DoesNotExist:
            form = EntryForm()
        else:
            form = EntryForm(initial = {'board' : b})
  
    return render(request, 'yighub/create.html', {'form' : form})

def edit(request, entry_id):
    try:
        e = Entry.objects.get(pk = entry_id)
    except Entry.DoesNotExist:
        messages.error(request, 'the entry does not exist')
        return render(request, 'yighub/error.html', context_instance = RequestContext(request))
    if request.method == 'POST':
        form = EntryForm(request.POST, instance = e)
        if form.is_valid():

            files = request.FILES.getlist('files')
            form.save()
            
            for f in e.files.all():
                try:
                    string = 'delete_' + str(f.id)
                    request.POST[string]
                except KeyError:
                    pass
                else:
                    f.file.delete()
                    f.delete()
            
            for file in files:
                f = File(entry = e, name = file.name, file = file)
                f.save()

            # 게시판 정보를 업데이트한다. - 필요한가?
            ##b = e.board
            ##b.newest_entry
            ##b.newest_time

            return redirect('yighub.views.read', entry_id = entry_id) #HttpResponseRedirect(reverse('yighub.views.read', args = (entry_id, )))
            
    else:
        form = EntryForm(initial = {'board' : e.board, 'title' : e.title, 'content' : e.content, 'notice' : e.notice})
        
        files = e.files.all()

    return render(request, 'yighub/edit.html', {'form' : form, 'files' : files, 'entry_id' : entry_id }, context_instance = RequestContext(request))


def delete(request, entry_id):
    
    # 권한 검사
    permission = is_member(request)
    if permission[0] == False:
        return permission[1]

    try:
        e = Entry.objects.get(pk = entry_id)
    except Entry.DoesNotExist:
        raise Http404


    if request.session['user'] == e.creator:
        files = e.files.all()
        for f in files:
            f.file.delete()

        # 게시판 정보를 업데이트한다.
        b = e.board
        b.count_entry -= 1
        if e.id == b.newest_entry:
            prev_entry = Entry.objects.filter(board = b).order_by('-arrangement')[1] # edit과 reply를 포함하면 time_last_modified로.
            b.newest_entry = prev_entry.id
            b.newest_time = prev_entry.time_last_modified
        b.save()

        e.delete()
    else:
        messages.error(request, 'invalid approach')
        return render(request, 'yighub/error.html', )
        #return render(request, 'yighub/error.html', {'error' : 'invalid approach'})
    return HttpResponseRedirect(reverse('yighub:home', ))

def reply(request, entry_id): # yig.in/entry/12345/reply     
    try:
        parent = Entry.objects.get(pk = entry_id)
    except Entry.DoesNotExist:
        raise Http404
    
    if request.method == 'POST':
        form = EntryForm(request.POST)
        if form.is_valid():

            files = request.FILES.getlist('files')
            
            current_depth = parent.depth + 1
            current_arrangement = parent.arrangement - 1
            p = entry_id
            range = Entry.objects.filter(arrangement__gt = (current_arrangement/1000) * 1000).filter(arrangement__lte = current_arrangement)
            
            while True:
                try:
                    q = range.filter(parent = p).order_by('arrangement')[0] 
                except IndexError:
                    break
                else:
                    current_arrangement = q.arrangement - 1
                    p = q.pk
            
            to_update = Entry.objects.filter(arrangement__gt = (current_arrangement/1000) * 1000 ).filter(arrangement__lte = current_arrangement)
            for e in to_update:
                e.arrangement -= 1
                e.save()

            reply = form.save(commit = False)
            reply.arrangement = current_arrangement
            reply.depth = current_depth
            reply.parent = entry_id
            reply.creator = request.session['user']
            reply.save()

            for file in files:
                f = File(entry = reply, name = file.name, file = file)
                f.save()

            # 게시판 정보를 업데이트한다.
            b = reply.board
            b.count_entry += 1
            b.save()

            return HttpResponseRedirect(reverse('yighub:home'))
    else:
        form = EntryForm(initial = {'board' : parent.board}) # board 빼고 보내기

    return render(request, 'yighub/reply.html', {'form' : form, 'parent' : entry_id}, ) 

def recommend(request, entry_id):

    # 권한 검사
    permission = is_member(request)
    if permission[0] == False:
        return permission[1]

    try:
        e = Entry.objects.get(pk = entry_id) 
    except Entry.DoesNotExist:
        raise Http404

    u = request.session['user']
    if u in e.recommendation.all():
        messages.error(request, 'You already recommend this')
        return render(request, 'yighub/error.html', )
    e.recommendation.add(u)
    e.count_recommendation += 1
    e.save()

    return redirect('yighub:read', entry_id = entry_id)

def delete_recommend(request, entry_id):
    
    # 권한 검사
    permission = is_member(request)
    if permission[0] == False:
        return permission[1]

    try:
        e = Entry.objects.get(pk = entry_id) 
    except Entry.DoesNotExist:
        raise Http404
    """
    u = request.session['user']
    if u in e.recommendation.all():
        d = e.recommendation.get(messages.error(request, 'You already recommend this')
    """
    return 0

def comment(request, entry_id):
    if request.method == 'POST':
        e = Entry.objects.get(pk = entry_id)
        try:
            newest_comment = Comment.objects.order_by('-arrangement')[0]
        except IndexError:
            arrangement = 0
        else:
            arrangement = (newest_comment.arrangement/1000 + 1) * 1000
        c = Comment(entry = e,
                    content = request.POST['content'],
                    creator = request.session['user'],
                    time_created = timezone.now(),
                    arrangement = arrangement,
                    )
        c.save()
        e.count_comment += 1
        e.save()

        return redirect('yighub:read', entry_id = entry_id) # HttpResponseRedirect(reverse('yighub.views.read', args = (entry_id)))
    else:
        messages.error(request, 'invalid approach')
        return render(request, 'yighub/error.html', )

def reply_comment(request, entry_id):
    if request.method == 'POST':
        e = Entry.objects.get(pk = entry_id)
        u = request.session['user']

        parent = Comment.objects.get(pk = int(request.POST['comment_id'])) # int error ?
        current_depth = parent.depth + 1
        current_arrangement = parent.arrangement + 1

        p = request.POST['comment_id']
        range = Comment.objects.filter(entry = e).filter(arrangement__gte = current_arrangement).filter(arrangement__lt = (parent.arrangement/1000 + 1) * 1000)

        while True:
            try:
                q = range.filter(parent = p).order_by('arrangement')[0] 
            except IndexError:
                break
            else:
                current_arrangement = q.arrangement + 1
                p = q.pk

        to_update = Comment.objects.filter(arrangement__gte = current_arrangement).filter(arrangement__lt = (current_arrangement/1000 + 1) * 1000 )
        for c in to_update:
            c.arrangement += 1
            c.save()

        reply_comment = Comment(entry = e,
                                content = request.POST['content'], 
                                creater = u, 
                                arrangement = current_arrangement,
                                depth = current_depth,
                                parent = request.POST['comment_id'],
                                )                                              
        reply_comment.save()

        return HttpResponseRedirect(reverse('yighub:home'))
    else:
        messages.error(request, 'invalid approach')
        return render(request, 'yighub/error.html', )

def recommend_comment(request, entry_id, comment_id):

    # 권한 검사
    permission = is_member(request)
    if permission[0] == False:
        return permission[1]

    c = Comment.objects.get(pk = comment_id)
    u = request.session['user']
    if u in c.recommendation.all():
        messages.error(request, 'You already recommend this')
        return render(request, 'yighub/error.html', context_instance = RequestContext(request))
    c.recommendation.add(u)
    c.count_recommendation += 1
    c.save()

    return redirect('yighub:read', entry_id = entry_id)

def delete_comment(request, ):
    pass


def intro(request, intro_name, current_page = 1):

    current_page = int(current_page)

    # 속한 게시판 알아내기
    for i in Intro.INTRO_BOARD_CHOICES:
        if intro_name in i:
            b = i[0]
            break
    try:
        test = b
    except:
        raise Http404

    # 글 가져오기
    try:
        e = Intro.objects.filter(board = b).order_by('-pk')[current_page - 1]
    except:
        class e:
            pass
    else:
        e.count_view += 1 

    # 첫 페이지와 끝 페이지 설정
    first_page = 1
    last_page = Intro.objects.filter(board = b).count()
    
    # 페이지 리스트 만들기
    if current_page < 5:
        start_page = 1
    else:
        start_page = current_page - 4

    if current_page > last_page - 5:
        end_page = last_page
    else:
        end_page = current_page + 4
    
    page_list = range(start_page, end_page + 1)

    # 이전 페이지, 다음 페이지 설정
    prev_page = current_page - 1
    next_page = current_page + 1
    
    # 맨 첫 페이지나 맨 끝 페이지일 때 고려
    if current_page == last_page:
        next_page = 0
        last_page = 0
    if current_page == first_page:
        prev_page = 0
        first_page = 0
    
    # 페이지 dictionary 만들기
    p = {'current_page' : current_page,
            'page_list' : page_list,
            'first_page' : first_page,
            'last_page' : last_page,
            'prev_page' : prev_page,
            'next_page' : next_page,
           }

    # 회원, 비회원 구분하기
    try:
        u = request.session['user_id']
        user = User.objects.get(user_id = u) # 세션에는 남아있지만 데이터베이스에는 없는 경우. 회원탈퇴이거나 다른 app을 쓰다 접근.
    except KeyError:
        member = False
    except User.DoesNotExist:
        return redirect('yighub.views.logout',)
    else:
        if user.level == 'non':
            member = False
        else:
            member = user


    if intro_name == 'introduction':
        return render(request, 'yighub/introduction.html', {'user' : member, 'entry' : e, 'page' : p }, )
    if intro_name == 'vision':
        return render(request, 'yighub/vision.html', {'user' : member, 'entry' : e, 'page' : p }, )
    if intro_name == 'activity':
        return render(request, 'yighub/activity.html', {'user' : member, 'entry' : e, 'page' : p }, )
    if intro_name == 'history':
        return render(request, 'yighub/history.html', {'user' : member, 'entry' : e, 'page' : p }, )
    if intro_name == 'clipping':
        return render(request, 'yighub/clipping.html', {'user' : member, 'entry' : e, 'page' : p }, )
    if intro_name == 'recruiting':
        return render(request, 'yighub/recruiting.html', {'user' : member, 'entry' : e, 'page' : p }, )
    if intro_name == 'schedule':
        return render(request, 'yighub/schedule.html', {'user' : member, 'entry' : e, 'page' : p }, )
    if intro_name == 'apply':
        return render(request, 'yighub/apply.html', {'user' : member, 'entry' : e, 'page' : p }, )
    if intro_name == 'universe':
        return render(request, 'yighub/universe.html', {'user' : member, 'entry' : e, 'page' : p }, )
    if intro_name == 'simA fund':
        return render(request, 'yighub/simA fund.html', {'user' : member, 'entry' : e, 'page' : p }, )
    if intro_name == 'simB fund':
        return render(request, 'yighub/simB fund.html', {'user' : member, 'entry' : e, 'page' : p }, )
    if intro_name == 'simV fund':
        return render(request, 'yighub/simV fund.html', {'user' : member, 'entry' : e, 'page' : p }, )
    if intro_name == 'contact us':
        return render(request, 'yighub/contact us.html', {'user' : member, 'entry' : e, 'page' : p }, )

def create_intro(request, intro_name ):
    
    # 속한 게시판 알아내기
    for i in Intro.INTRO_BOARD_CHOICES:
        if intro_name in i:
            b = i[0]
            break
    try:
        test = b
    except:
        raise Http404

    if request.method == 'POST':
        form = IntroForm(request.POST)
        if form.is_valid():

            form.save()

            return redirect('yighub.views.intro', {'intro_name' : intro_name} )
    else:
        form = IntroForm(initial = {'board' : b}) # 반드시 intro_name을 지정해야 함. /intro/create는 불가능.

    return render(request, 'yighub/create_intro.html', {'form' : form, 'intro_name' : intro_name}, context_instance = RequestContext(request))


def edit_intro(request, ):
    pass

def delete_intro(request, ):
    pass




def join(request):
    if request.method == 'POST':
        form = UserForm(request.POST, request.FILES)
        if form.is_valid():
            f = form.save(commit = False)
            f.password = hashers.make_password(request.POST['password'])
            f.last_login = timezone.now()
            f.level = 'non'
            f.save()
            return redirect('yighub:home', )
    else:
        form = UserForm()

    return render(request, 'yighub/join.html', {'form' : form}, context_instance = RequestContext(request))

def edit_profile(request):
    pass

def delete_profile(request):
    pass

def login(request):
    request.session.set_test_cookie()
    return render(request, 'yighub/login.html')
    
def login_check(request):
    try:
        u = User.objects.get(user_id = request.POST['user_id'])
    except User.DoesNotExist:
        messages.error(request, 'incorrect user id')
        return render(request, 'yighub/error.html', )

    if request.session.test_cookie_worked():
        if hashers.check_password(request.POST['password'], u.password):
            request.session['user_id'] = u.user_id
            request.session['user'] = u

            return HttpResponseRedirect(reverse('yighub:home'))
        else:
            messages.error(request, 'login failed') # send message 
            return render(request, 'yighub/error.html')
    else:
        # send message about cookie
        messages.error(request, 'please enable cookie')
        return render(request, 'yighub/error.html')

def logout(request):
    request.session.flush() # exact functionality of flush method? after flush, home_for_visitor is presenting?
    return HttpResponseRedirect(reverse('yighub:home'))

def send(request):
    if request.method == 'POST':
        form = LetterForm(request.POST, request.FILES)
        if form.is_valid():

            s = form.save(commit = False)
            s.sender = request.session['user']
            s.file_name = request.FILES['file'].name
            s.save()

            return redirect('yighub.views.receive', )
    else:
        form = LetterForm()

    return render(request, 'yighub/send.html', {'form' : form}, context_instance = RequestContext(request))
 
         
def letters(request):
    u = request.POST['user']
    letters = Letter.objects.filter(receiver = u)

    # 페이지 넘기기 설정하기

    return render(request, 'yighub/letters.html', {'letters' : letters, })

def receive(request, letter_id): 

    if is_member(request):
        pass

    try:
        l = Letter.objects.get(pk = letter_id)
    except Letter.DoesNotExist:
        raise Http404
    
    u = request.POST['user']
    
    if l.receiver == u:
        l.read = True
        l.save()
        return render(request, 'yighub/receive.html', {'letter' : l})
    else:
        messages.error(request, 'Not You')
        return render(request, 'yighub/error.html', context_instance = RequestContext(request))

def create_memo(request):
    if request.method == 'POST':
        m = Memo(memo = request.POST['memo'],
                 creator = request.session['user'],
                 time_created = timezone.now(),
                )
        m.save()
        
        return redirect('yighub.views.home', ) # HttpResponseRedirect(reverse('yighub.views.read', args = (entry_id)))
    else:
        messages.error(request, 'invalid approach')
        return render(request, 'yighub/error.html', context_instance = RequestContext(request))

def download(request, file_id):
    f = File.objects.get(pk = file_id)
    path = f.file.path
    fp = open(path,'rb')
    response = HttpResponse(fp.read())
    fp.close()
    
    f.hit += 1
    f.save()
    
    type, encoding = mimetypes.guess_type(f.file.name)
    #if type is None:
    #    type = 'application/octet-stream'
    response['Content-Type'] = type
    response['Content-Encoding'] = encoding
#    encoded_name = f.file.name.encode(encoding = 'UTF-8')
#    response['Content-Disposition'] = u'attachment; filename=%s' % encoded_name

    return response

def download_intro(request, intro_id): # 권한 체크하지 않음.
    pass 

def download_letter(request, letter_id):
    pass