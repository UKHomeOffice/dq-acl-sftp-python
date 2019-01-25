FROM centos:7

ARG USER_ID=14
ARG GROUP_ID=50

COPY vsftpd.conf /etc/vsftpd/
COPY vsftpd_virtual /etc/pam.d/
COPY run-vsftpd.sh /usr/sbin/

ENV FTP_USER **String**
ENV FTP_PASS **Random**
ENV PASV_ADDRESS **IPv4**
ENV PASV_ADDR_RESOLVE NO
ENV PASV_ENABLE YES
ENV PASV_MIN_PORT 6000
ENV PASV_MAX_PORT 6010
ENV LOG_STDOUT YES
ENV FILE_OPEN_MODE 0666
ENV LOCAL_UMASK 077

RUN usermod -u ${USER_ID} ftp
RUN groupmod -g ${GROUP_ID} ftp

RUN yum update -y && \
    yum install vsftpd ftp iptables-services -y && \
    systemctl enable vsftpd

RUN chmod +x /usr/sbin/run-vsftpd.sh
RUN mkdir -p /home/vsftpd/
RUN chown -R ftp:ftp /home/vsftpd/

VOLUME /home/vsftpd
VOLUME /var/log/vsftpd

EXPOSE 20 21 6000:6010

CMD ["/usr/sbin/run-vsftpd.sh"]
