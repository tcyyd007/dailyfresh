from django.core.urlresolvers import reverse
from django.shortcuts import render, redirect
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from itsdangerous import SignatureExpired
from django.http import  HttpResponse
import re
from django.views.generic import View
from user.models import User
from django.conf import settings
from celery_tasks.tasks import send_register_active_email

class RegisterView(View):
    '''注册'''
    def get(self,request):
        '''返回注册页面'''
        return render(request, 'register.html')
    '''注册处理'''
    def post(self,request):
        '''进行注册处理'''
        # 接受数据
        username = request.POST.get('user_name')
        password = request.POST.get('pwd')
        email = request.POST.get('email')
        allow = request.POST.get('allow')  # 用户是否同意

        # 进行数据校验
        if not all([username, password, email]):
            # 数据不完整
            return render(request, 'register.html', {'errmsg': '数据不完整'})
        # 校验邮箱
        if not re.match(r'^[a-z0-9][\w.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
            return render(request, 'register.html', {'errmsg': '邮箱格式不正确'})
        if allow != 'on':
            return render(request, 'register.html', {'errmsg': '请同意协议'})
        # 校验用户名是否重复
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            # 用户名不存在
            user = None
        if user:
            # 用户名已存在
            return render(request, 'register.html', {'errmsg': '用户名已存在'})
        # 进行业务处理:进行用户注册
        # user = User()
        # user.username=username;
        # user.password=password;
        # ...
        # user.save()

        # 因为继承的是django默认的认证模块,所以用django封装好的创建用户的方法就可以
        # 上面的等于下面的代码
        user = User.objects.create_user(username, email, password)
        user.is_active = 0  # 刚注册的用户不应该是被激活的所以设置为0
        user.save()

        #发送激活邮件,包含激活链接: http://127.0.0.1:8000/user/active/3
        #链接中需要包含用的的身份信息,并且要把身份信息进行加密

        #加密用户的身份信息,生成激活token
        serializer = Serializer(settings.SECRET_KEY,3600)#用到了settings类里的django生成的密钥  也可以自己随便写
        info={'confirm':user.id}#要加密的内容
        token = serializer.dumps(info)#加密返回加密后的结果
        token=token.decode()#因为dumps返回的是bytes数组 要进行解码

        #发邮件
        send_register_active_email.delay(email,username,token)

        # 返回应答,跳转到首页
        # return render(request, 'register.html', {'errmsg': token}) #测试token
        return redirect(reverse('goods:index'))




class ActiveView(View):
    '''用户激活'''
    def get(self,request,token):
        '''进行用户激活'''
        #进行解密,获取要激活的用户信息
        serializer = Serializer(settings.SECRET_KEY,3600)#用到了settings类里的django生成的密钥  也可以自己随便写
        try:
           info= serializer.loads(token)
            #获取待激活用户的id
           user_id = info['confirm']
           #根据id获取用户信息
           user=User.objects.get(id=user_id)
           #改变这个用户的激活标识
           user.is_active=1
           user.save()

           #跳转到登陆页面
           return redirect(reverse('user:login'))

        except SignatureExpired as e:
            return HttpResponse('激活连接已过期')

class LoginView(View):
    '''登陆'''
    def get(self,request):
        '''显示登陆页面'''
        return render(request,'login.html')