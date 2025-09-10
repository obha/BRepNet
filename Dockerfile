# this is a docker image with conda environment with brepnet installed
FROM continuumio/miniconda3
COPY environment.yml /
RUN conda env create -f /environment.yml
# Make RUN commands use the new environment:
SHELL ["conda", "run", "-n", "brepnet", "/bin/bash", "-c"]
# The code to run when container is started:
COPY . /brepnet
WORKDIR /brepnet
RUN pip install -e .
CMD ["python", "-c", "import brepnet; print(brepnet.__version__)"]
# CMD ["python", "-c", "from brepnet.models.brepnet import BRepNet; print('OK')"]