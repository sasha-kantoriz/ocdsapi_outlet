""" s3.py - amazon s3 storage backend """
import os
import os.path
import logging
import click
from . import BACKENDS
from .base import BaseOutlet, BaseHandler
from ..run import cli
from ..dumptool import OCDSPacker
from ..utils import connect_bucket
from ..config import make_config


LOGGER = logging.getLogger('ocdsapi.outlet.dumptool')
DEFAULT_RENDERER = 'json'


class S3BucketHandler(BaseHandler):
    """ Writes releases to s3 bucket """

    def __init__(self, cfg, base_package):
        super().__init__(cfg, base_package)
        self.bucket, self.client = connect_bucket(cfg)
        self.bucket_location = self.client.get_bucket_location(Bucket=self.bucket)
        self.name = '{}.json'.format(self.base_package['publishedDate'])

    def write_releases(self, releases):
        """ Handle one release """
        self.base_package['releases'] = releases
        prefix = self.cfg.key_prefix
        key = os.path.join(prefix, self.base_package['uri'])
        try:
            self.client.put_object(
                Body=self.renderer.dumps(self.base_package),
                Bucket=self.bucket,
                Key=key
            )
            if self.cfg.manifest:
                self.cfg.manifest.releases.append(
                    "https://s3-{0}.amazonaws.com/{1}/{2}".format(
                        self.bucket_location['LocationConstraint'],
                        self.bucket.name,
                        key
                    )
                )
        except self.client.exceptions.ClientError as e:
            self.logger.fatal("Failed to upload object to s3. Error: {}".format(
                e
            ))
        finally:
            del self.base_package['releases']


class S3Outlet(BaseOutlet):
    """ S3 backend main class """
    def __init__(self, cfg):
        super().__init__(S3BucketHandler, cfg)


@click.command(name='s3')
@click.option(
    '--bucket',
    help="Destination path to store static dump",
    required=True
    )
@click.option(
    '--aws-access-key',
    help='AWS access key id. If not provided will be taken from environment',
    required=False
)
@click.option(
    '--aws-secred-key',
    help='AWS access secred key. If not provided will be taken from environment',
    required=False
)
@click.pass_context
def s3(ctx, bucket, aws_access_key, aws_secred_key):
    ctx.obj['backend'] = S3Outlet
    cfg = make_config(ctx)
    cfg.aws_access_key = aws_access_key
    cfg.aws_secred_key = aws_secred_key
    cfg.bucket = bucket
    packer = OCDSPacker(cfg)
    packer.run()


def install():
    cli.add_command(s3, 's3')
    BACKENDS['s3'] = S3Outlet
