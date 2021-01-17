import os

S3_BUCKET= os.environ.get('S3_BUCKET')
S3_Key= os.environ.get('S3_Key')
S3_SECRET= os.environ.get('S3_SECRET')
S3_LOCATION='http://{}.s3.eu-west-3.amazonaws.com/'.format(S3_BUCKET)
SECRET_KEY= os.environ.get('SECRET_KEY')