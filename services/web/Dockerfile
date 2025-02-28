# Use Ubuntu as the base image
FROM ubuntu:22.04

# Set environment variables to reduce installation warnings
ENV DEBIAN_FRONTEND=noninteractive

# Set the working directory in the container
WORKDIR /usr/src/app

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install system dependencies and Python 3.11
RUN apt-get update && apt-get install -y \
    software-properties-common \
    curl \
    wget \
    unzip \
    openjdk-11-jdk \
    libx11-dev \
    libxext-dev \
    libxrender-dev \
    libxtst-dev \
    zlib1g-dev \
    libbz2-dev \
    liblzma-dev \
    libncurses5-dev \
    build-essential \
    python3-pip \
    python3-dev \
    bzip2 \
    libbz2-dev \
    liblzma-dev \
    netcat \
    bedtools \
    nodejs \
    npm \
    && apt-get clean

# Install jsdoc globally
RUN npm install -g jsdoc@4.0.4

# Make the Conda environment available globally
ENV PATH="/opt/conda/envs/busco_env/bin:$PATH"

# Install Qualimap
RUN wget https://bitbucket.org/kokonech/qualimap/downloads/qualimap_v2.3.zip && \
    unzip qualimap_v2.3.zip && \
    rm qualimap_v2.3.zip && \
    mv qualimap_v2.3 /opt/qualimap

# Add Qualimap to PATH
ENV PATH="/opt/qualimap:$PATH"

# Install Nextclade CLI
RUN curl -fsSL "https://github.com/nextstrain/nextclade/releases/download/3.9.1/nextclade-x86_64-unknown-linux-gnu" -o "nextclade" && chmod +x nextclade && mv nextclade /usr/local/bin/

# install Hmmer
RUN wget http://eddylab.org/software/hmmer/hmmer-3.1b2.tar.gz && tar xvfz hmmer-3.1b2.tar.gz && \
	cd hmmer-3.1b2 && ./configure && make && make install && cd ..

# install Augustus
RUN apt install -y augustus augustus-data augustus-doc && \
	wget -O /usr/bin/augustus https://github.com/Gaius-Augustus/Augustus/releases/download/3.3.2/augustus
ENV AUGUSTUS_CONFIG_PATH /usr/share/augustus/config

# install BUSCO and set the default in the scripts to python3 so I don't have to type it each time
# and full path each time when called
RUN apt-get install git -y && \
	git clone --recursive https://gitlab.com/ezlab/busco.git && \
	cd busco && \
	python3 -m pip install .
    
# Install Python dependencies from requirements.txt
COPY requirements.txt /usr/src/app/
RUN python3 -m pip install --no-cache-dir -r requirements.txt --ignore-install

# Clone and make bwa
RUN git clone https://github.com/lh3/bwa.git --branch v0.7.18 && cd bwa && make && mv bwa /usr/local/bin/

# Clone and make minimap2
RUN git clone https://github.com/lh3/minimap2 --branch v2.28 && cd minimap2 && make && mv minimap2 /usr/local/bin/

# set bwa executable as env variable
ENV BWA=/usr/src/app/bwa/bwa

# Install nextflow (24.10.3)
RUN curl -s https://get.nextflow.io | bash && chmod +x nextflow && mv nextflow /usr/local/bin/

# BBDuk
ENV BB_VERSION="39.13"
RUN cd / && wget "https://sourceforge.net/projects/bbmap/files/BBMap_${BB_VERSION}.tar.gz/download" && tar xf download

#iVar and htslib
RUN wget https://github.com/samtools/htslib/releases/download/1.21/htslib-1.21.tar.bz2 && tar -xf htslib-1.21.tar.bz2 && cd htslib-1.21 && ./configure --prefix=/usr/bin/htslib-1.21 && make && make install
RUN wget https://github.com/samtools/bcftools/releases/download/1.21/bcftools-1.21.tar.bz2 && tar -xf bcftools-1.21.tar.bz2 && cd bcftools-1.21 && ./configure --prefix=/usr/bin/bcftools-1.21 && make && make install
RUN export PATH=/usr/bin/htslib-1.21/bin:$PATH
RUN apt-get install autotools-dev autoconf -y && git clone https://github.com/andersen-lab/ivar.git --branch v1.4.3 && cd ivar && ./autogen.sh && ./configure --with-hts=/usr/bin/htslib-1.21 && make && make install

# Verify installations
RUN java -version && /opt/qualimap/qualimap --help && nextclade --version && busco --version && nextflow info && /bbmap/bbduk.sh -h && ivar version && bedtools --version

# Libreoffice to convert docx to pdf
RUN apt install -y libreoffice

# Copy the rest of the application's source code to the container
COPY project/ main.nf entrypoint.sh manage.py /usr/src/app/

# run entrypoint.sh
ENTRYPOINT ["/usr/src/app/entrypoint.sh"]

# Expose the Flask app port
#EXPOSE 5000

# Define the command to run the Flask app
#CMD ["python3", "app.py"]

# Build: sudo docker build -t neqas/back .
# Run: sudo docker run  -p 5000:5000 neqas/back

