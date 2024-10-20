FROM public.ecr.aws/lambda/python:3.9

# Copy function code
COPY app.py ${LAMBDA_TASK_ROOT}

# Install the function's dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt --target "${LAMBDA_TASK_ROOT}"

# Set the CMD to your handler
CMD [ "app.lambda_handler" ]