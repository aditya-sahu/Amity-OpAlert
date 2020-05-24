from flask import Flask, render_template, request, session, flash, url_for
import datetime
from itsdangerous import URLSafeTimedSerializer
from flask_mail import Mail, Message
from bs4 import BeautifulSoup
import requests
import pymongo


app = Flask(__name__)
app.secret_key = "yess"
app.config.from_pyfile('config.py')

app.config.update(dict(
    DEBUG = True,
    MAIL_SERVER = 'smtp.gmail.com',
    MAIL_PORT = 465,
    MAIL_USE_TLS = False,
    MAIL_USE_SSL = True,
    MAIL_USERNAME = 'amityopalert@gmail.com',
    MAIL_PASSWORD = '98@addykool15',
))

mail = Mail()
mail.init_app(app)
confirm_serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])    

client = pymongo.MongoClient("mongodb+srv://addy98:98%40addykool15@cluster-amity-opalert-rxvbh.mongodb.net/test?retryWrites=true&w=majority")
db = client.amityopdb
AmityUserCollection = db.AmityUserCollection
AmityOpportunityCollection = db.AmityOpportunity

def send_confirmation_email(user_email):
    confirm_url = url_for('confirm_email', token=confirm_serializer.dumps(user_email, salt='email-confirmation-salt'),_external=True)
 
    html = render_template(
        'email_confirmation.html',
        confirm_url=confirm_url)
    msg = Message(subject='OpAmity Registration', body='Thanks for joining OpAmity! To verify your account, visit the url and activate it: '+confirm_url, sender="email", recipients=[user_email])
    mail.send(msg)

def send_unsubscribe_email(user_email):
    confirm_url = url_for(
        'unsubscribe_email',
        token=confirm_serializer.dumps(user_email, salt='email-unsubscription-salt'),
        _external=True)
 
    html = render_template(
        'email_unsubscribe.html',
        confirm_url=confirm_url)
    msg = Message(subject='We tried our best.', body='We\'re sorry to see you go from Amity OpAlert! To confirm your unsubscription, visit the url and activate it: '+confirm_url, sender="email", recipients=[user_email])
    mail.send(msg)


def getData():
    now = datetime.datetime.now().year
    page = requests.get('http://amity.edu/placement/upcoming-recruitment.asp')
    soup = BeautifulSoup(page.text, 'html.parser')

    # Find the respective opname,opurl,opyear and submit data to DB
    # When submitting to DB also send email to respective users

    # Prepare list of tuples with opname, opyear, opurl
    soup = soup.find(class_='notices')
    soupURLS = soup.find_all('a', href=True)
    soupNAMES = soup.find_all('strong')
    arr = []
    for i in soupNAMES:
        i = i.string
        if(i.find(str(now)) != -1):
            arr.append((i,str(now)))
        elif(i.find(str(now-1))!=-1):
            arr.append((i,str(now-1)))
        elif(i.find(str(now+1))!=-1):
            arr.append((i,str(now+1)))
        elif(i.find(str(now+2))!=-1):
            arr.append((i,str(now+2)))
        else:
            arr.append((i,'0'))
    index = 0
    for i in soupURLS:
        url='https://amity.edu/placement/'+i['href']
        tmplist = list(arr[index])
        tmplist.append(url)
        arr[index] = tuple(tmplist)
        index = index + 1
    return arr

def storeData(arr):
    for i in arr:
        #Check if data already exists in db.. if so, then do nothing
        if(AmityOpportunityCollection.count_documents({"opurl":i[2]})==0):
            if((AmityUserCollection.count_documents({"yearOfGrad":i[1],"email_confirmed":True})==0)):
                return
            if(i[1]==0):
                receivers = AmityUserCollection.find({"email_confirmed":True})
            else:
                receivers = AmityUserCollection.find({"yearOfGrad":i[1],"email_confirmed":True})
            print(i[1])
            receiver=[]
            for some in receivers:
                receiver.append(some["emailId"])
            print(receiver)
            if(len(receiver)>0):
                print('sending mail to ',receiver)
                msg = Message(subject='New Opportunity: '+i[0], body=i[0]+': '+i[2], sender="email", bcc=receiver)
                mail.send(msg)
            op=AmityOpportunityCollection.insert_one({"opname":i[0],"opyear":i[1],"opurl":i[2]}).inserted_id
            print(op)
        else:
            print('already')

def deleteExpiredOpportunities():
     mydata = AmityOpportunityCollection.find()
     receiveddata = getData()
     flag = False
     for i in mydata:
         for j in receiveddata:
             if(i['opurl'] == j[2]):
                 flag = True
                 break
             else:
                 flag = False
         if(flag==False):
             print('removing op from DB: '+i['opname'])
             print(i["opurl"])
             if(AmityOpportunityCollection.count_documents({"opurl":i["opurl"]})==0):
                 return
             AmityOpportunityCollection.delete_one({"opurl":i["opurl"]})

@app.route('/')
def index():
    now = datetime.datetime.now().year
    return render_template('index.html',now=now)

@app.route('/yourself')
def yourself():
    return render_template('yourself.html')

@app.route('/donate')
def donate():
    return render_template('donate.html')


@app.route('/about')
def about():
    now = datetime.datetime.now()
    birthdate = datetime.datetime(1998, 11, 15, 12, 20)
    years = (birthdate - now).total_seconds() / (365.242*24*3600)
    yearsInt = int(years)
    
    months = (years-yearsInt) * 12
    monthsInt = int(months)
    
    days = (months-monthsInt)*(365.242/12)
    daysInt = int(days)
    
    secondold = (now - birthdate).seconds
    return render_template('about.html', now=now, yearold = -yearsInt, monthold= -monthsInt, dayold = -daysInt)


@app.route('/submit', methods = ['POST'])
def submitted():
    email = request.form['email']
    year = request.form['year']

    #Check if the email address is already in database, if so, render email already exists page
    print(AmityUserCollection.count_documents({"emailId":email}))
    if(AmityUserCollection.count_documents({"emailId":email})>0):
        return render_template('emailexists.html')
    else:
        AmityUserCollection.insert_one({"registeredOn":datetime.datetime.now(), "emailId":email, "yearOfGrad":year, "email_confirmed":False})
    send_confirmation_email(email)
    return render_template('email_confirmation.html')

@app.route('/unsubscribe')
def unsubscribe():
    return render_template('email_unsubscribe.html')

@app.route('/email_unsubscribe_submit', methods = ['POST'])
def email_unsubscribe_submitted():
    email = request.form['email']

    #Check if the email address is not in database, if so, render email not exists page
    print(AmityUserCollection.count_documents({"emailId":email}))
    if(AmityUserCollection.count_documents({"emailId":email}) == 0):
        return render_template('emailnotexists.html')
    send_unsubscribe_email(email)
    return render_template('email_unsubscribe_submitted.html')

@app.route('/unsubscribe_email/<token>')
def unsubscribe_email(token):
    try:
        email = confirm_serializer.loads(token,salt='email-unsubscription-salt',max_age=86400)
    except:
        abort(404)
    AmityUserCollection.delete_one({"emailId":email})
    return render_template('email_unsubscribed.html')


@app.route('/confirm_email/<token>')
def confirm_email(token):
    try:
        email = confirm_serializer.loads(token,salt='email-confirmation-salt',max_age=86400)
    except:
        abort(404)
    AmityUserCollection.update_one({"emailId":email},{"$set":{"email_confirmed":True}})
    return render_template('email_confirmed.html')

@app.route('/cronJob1234', methods = ['GET'])
def runThisCron():
    arr= getData()
    storeData(arr)
    AmityUserCollection.delete_many({"email_confirmed":False})
    deleteExpiredOpportunities()

    
    return 'cronJob has been run on '+ str(datetime.datetime.now())

