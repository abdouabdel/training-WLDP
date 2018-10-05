# inherit defined based image
FROM centos:7

# define a mailing-list maintainer
MAINTAINER WLDP Development <dl-fr-deepsky-moe@atos.net>

# port(s) exposed (avoid privileged ports if you target openshift - >1024)
EXPOSE 8080

# labels are optional but still a good way to do
# learn more at: https://docs.openshift.org/{{book.osversion}}/creating_images/metadata.html
LABEL io.k8s.description="WLDP Traning - Step 1 - Hello" \
  io.k8s.display-name="LDP Traning - Step 1 - Hello" \
  io.openshift.expose-services="8080:http" \
  io.openshift.tags="wldp,training"

# install required package(s) in a single package manager transaction and clean up just after to reduce image size
RUN INSTALL_PKGS="python" && \ 
	yum install -y $INSTALL_PKGS && \
	rpm -V $INSTALL_PKGS && \
	yum clean all

# define required environment variable
ENV HOME=/opt/app-root/src PYTHONUNBUFFERED=true

# add you application artifact(s) and entrypoint script
# for interpreted languages like python, there is no build step and artifact is the source code itself
ADD src/app.py run.sh ${HOME}/

# set the image working directory and user - other than root/0
WORKDIR ${HOME}
USER 1001

# define the starting command: calling 'sh run.sh'' instead if just 'run.sh' is a good habit that prevent you from setting x right to run.sh
CMD ["sh", "/opt/app-root/src/run.sh"]
