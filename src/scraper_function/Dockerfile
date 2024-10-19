# Use the official AWS Lambda Python image as the base
FROM amazon/aws-lambda-python:3.9

# Install Chrome and its dependencies
RUN dnf install -y atk cups-libs gtk3 libXcomposite alsa-lib \
    libXcursor libXdamage libXext libXi libXrandr libXScrnSaver \
    libXtst pango at-spi2-atk libXt xorg-x11-server-Xvfb \
    xorg-x11-xauth dbus-glib dbus-glib-devel nss mesa-libgbm jq unzip

# Copy and run the Chrome installation script
COPY ./chrome-installer.sh ./chrome-installer.sh
RUN chmod +x ./chrome-installer.sh && ./chrome-installer.sh
RUN rm ./chrome-installer.sh

# Install Python dependencies, including Selenium
COPY requirements.txt ./
RUN pip install -r requirements.txt

# Copy the main application code
COPY app.py ./
COPY utils.py ./

# Set the command to run your Lambda function
CMD ["app.lambda_handler"]
