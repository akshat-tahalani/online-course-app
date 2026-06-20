from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from .models import Course, Enrollment, Question, Choice, Submission


def registration_request(request):
    context = {}
    if request.method == 'GET':
        return render(request, 'onlinecourse/user_registration_bootstrap.html', context)
    elif request.method == 'POST':
        username = request.POST['username']
        password = request.POST['psw']
        first_name = request.POST['firstname']
        last_name = request.POST['lastname']
        if User.objects.filter(username=username).exists():
            context['message'] = "User already exists."
            return render(request, 'onlinecourse/user_registration_bootstrap.html', context)
        user = User.objects.create_user(
            username=username, first_name=first_name, last_name=last_name, password=password
        )
        login(request, user)
        return redirect("onlinecourse:index")


def login_request(request):
    context = {}
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['psw']
        user = authenticate(username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('onlinecourse:index')
        context['message'] = "Invalid username or password."
        return render(request, 'onlinecourse/user_login_bootstrap.html', context)
    return render(request, 'onlinecourse/user_login_bootstrap.html', context)


def logout_request(request):
    logout(request)
    return redirect('onlinecourse:index')


def course_list(request):
    courses = Course.objects.order_by('-total_enrollment')[:10]
    if request.user.is_authenticated:
        for course in courses:
            course.is_enrolled = Enrollment.objects.filter(user=request.user, course=course).exists()
    return render(request, 'onlinecourse/course_list_bootstrap.html', {'course_list': courses})


def course_details(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    course.is_enrolled = False
    if request.user.is_authenticated:
        course.is_enrolled = Enrollment.objects.filter(user=request.user, course=course).exists()
    return render(request, 'onlinecourse/course_details_bootstrap.html', {'course': course})


def enroll(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    user = request.user
    if not Enrollment.objects.filter(user=user, course=course).exists():
        Enrollment.objects.create(user=user, course=course, mode='honor')
        course.total_enrollment += 1
        course.save()
    return redirect('onlinecourse:course_details', course_id=course_id)


def submit(request, course_id):
    if not request.user.is_authenticated:
        return redirect('onlinecourse:login')
    
    course = get_object_or_404(Course, pk=course_id)
    user = request.user
    enrollment = get_object_or_404(Enrollment, user=user, course=course)
    submission = Submission.objects.create(enrollment=enrollment)
    
    # Process selected answers
    selected_ids = []
    for key in request.POST:
        if key.startswith('choice_'):
            try:
                selected_ids.append(int(request.POST[key]))
            except (ValueError, KeyError):
                pass
    
    # Get all choices and add them to submission
    selected_choices = Choice.objects.filter(id__in=selected_ids)
    submission.choices.set(selected_choices)
    
    # Calculate score and build question breakdown
    score = 0
    questions = course.question_set.all()
    question_results = []
    
    for question in questions:
        question_selected_ids = [choice.id for choice in selected_choices if choice.question == question]
        is_correct = question.is_get_score(question_selected_ids)
        
        if is_correct:
            score += question.grade
        
        # Build choice feedback for this question
        choice_results = []
        for choice in question.choice_set.all():
            choice_dict = {
                'content': choice.content,
                'is_correct': choice.is_correct,
                'selected': choice.id in question_selected_ids
            }
            
            # Determine color/status
            if choice.is_correct and choice.id in question_selected_ids:
                choice_dict['status'] = 'correct'  # Green
            elif not choice.is_correct and choice.id in question_selected_ids:
                choice_dict['status'] = 'wrong'  # Red
            elif choice.is_correct and choice.id not in question_selected_ids:
                choice_dict['status'] = 'not_selected'  # Yellow (missed correct answer)
            else:
                choice_dict['status'] = 'unselected'  # Not selected and not correct
            
            choice_results.append(choice_dict)
        
        question_results.append({
            'content': question.content,
            'grade': question.grade,
            'is_correct': is_correct,
            'choices': choice_results
        })
    
    max_score = sum(q.grade for q in questions)
    percentage = (score / max_score * 100) if max_score > 0 else 0
    is_passed = percentage >= 50  # Pass if 50% or higher
    
    context = {
        'course': course,
        'submission': submission,
        'score': score,
        'max_score': max_score,
        'percentage': round(percentage, 1),
        'is_passed': is_passed,
        'question_results': question_results,
        'user_name': user.first_name or user.username
    }
    return render(request, 'onlinecourse/submission_result.html', context)