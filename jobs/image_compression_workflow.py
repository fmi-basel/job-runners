#!/usr/bin/env python

"""
image_compression_workflow.py:

Demo workflow for compressing image data.
The workflow itself is given as follows:

    FileListTask -> ImageCompressionTask
"""

import abc
from datetime import datetime, timedelta, time
import glob
import logging
import luigi
import os
from pathlib import Path
from PIL import Image  # TODO: remove
import re
import requests
import sys

from base_workflows import JobSystemWorkflow, ObservableJobSystemWorkflow


class FileListTask(luigi.Task):
    task_namespace = 'demo'

    search_path = luigi.Parameter(default="")
    recursive = luigi.BoolParameter(default=False)
    regex = luigi.Parameter(default="*.*")

    def requires(self):
        """
        Method which returns a list of tasks which have to exist before
        running FileListTask.

        :return: the list of required tasks
        """
        return []

    def run(self):
        """
        Main method.
        """
        if not self.search_path.endswith('/'):
            self.search_path += '/'
        with self.output().open("w") as file_list:
            for path in Path(self.search_path).glob(
                '**/*' if self.recursive else '*'
            ):
                if path.name.startswith("file_list.csv"):
                    continue
                if path.is_file() and re.match(self.regex, path.as_posix()):
                    file_list.write(path.as_posix() + "\n")

    def output(self):
        """
        Method which returns the task's target.

        :return: local target to file list
        """
        return luigi.LocalTarget(self.search_path + "/file_list.csv")


class ImageCompressionTask(luigi.Task):
    task_namespace = 'demo'

    search_path = luigi.Parameter(default="")
    recursive = luigi.BoolParameter(default=False)

    def requires(self):
        """
        Method which returns a list of tasks which have to exist before
        running ImageCompressionTask.

        :return: the list of required tasks
        """
        return FileListTask(
            self.search_path, self.recursive,
            ".*\.(tif{1,2}|png|gif|bmp|jpg|jpeg)$"
        )

    def run(self):
        """
        Main method.
        """
        self.notify_observers(status="in progress", progress=0)
        processed_files = 0

        if not os.path.exists(self.search_path + "/TIFF/"):
            os.makedirs(self.search_path + "/TIFF/")

        with self.input().open() as file_list:
            with self.output().open('w') as compr_file_list:
                for file_path in file_list:
                    file_path = file_path.strip()
                    file_name = os.path.basename(file_path)
                    if os.path.exists(
                        self.search_path + "/TIFF/" + file_name
                    ):
                        continue

                    try:
                        image = Image.open(file_path)
                        # if image.mode == "I;16":
                        if True:
                            image.save(
                                self.search_path + "/TIFF/" + file_name,
                                compression="tiff_lzw"
                            )
                        else:
                            raise RuntimeError(
                                "Unexpected image format found for '%s'!" % (
                                    file_name
                                )
                            )
                        # image = cv2.imread(file_path, cv2.IMREAD_UNCHANGED)
                        # cv2.imwrite(
                        #     # compress the image with LZW by default
                        #     self.search_path + "/TIFF/" + file_name,
                        #     np.uint16(image)
                        # )
                        compr_file_list.write(
                            self.search_path + "/TIFF/" + file_name + "\n"
                        )
                    except Exception as ex:
                        logging.getLogger('luigi-interface').error(ex)
                        continue

    def output(self):
        """
        Method which returns the task's target.

        :return: local target to file list with compressed images
        """
        return luigi.LocalTarget(self.search_path + "/compr_file_list.csv")


class ImageCompressionWorkflow(ObservableJobSystemWorkflow):
    """
    Workflow for compressing images.
    """
    task_namespace = 'demo'

    search_path = luigi.Parameter(default="")
    """
    search path for experiment folders.
    """
    recursive = luigi.BoolParameter(default=False)
    """
    activate depth search; does not only consider child folders relative to
    the search path.
    """

    def requires(self):
        task = ImageCompressionTask(self.search_path, self.recursive)
        # add the JobSystemWorkflow.notify_observers() method to
        # the ImageCompressionTask object
        task.notify_observers = self.notify_observers.__get__(task)
        return [task]

    def run(self):
        # use notifications only in run() methods - other methods,
        # e.g. requires(), are called multiple times from the luigi engine
        self.notify_observers(status="in progress", progress=100)