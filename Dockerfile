FROM ubuntu:22.04
ENV TZ=Etc/UTC
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN apt-get update \
  && apt-get install -y --no-install-recommends \
  ca-certificates gdal-bin python3 python3-pip wget \
  && rm -rf /var/lib/apt/lists/*


RUN wget https://aka.ms/downloadazcopy-v10-linux \
  && tar -xvf downloadazcopy-v10-linux \
  && cp azcopy_linux_amd64_*/azcopy /usr/bin/ \
  && chmod 755 /usr/bin/azcopy \
  && rm -f downloadazcopy-v10-linux \
  && rm -rf azcopy_linux_amd64_* \


WORKDIR /usr/src/app

COPY . .

RUN pip3 install --no-cache-dir -r requirements.txt

ENTRYPOINT ["python3", "check_countries.py"]

# Run the script after in
CMD ["admin"]

