#!/Users/cmj/Documents/Projects/remarkable-tool/venv/bin/python3

import click
import paramiko
import logging
import json
from tabulate import tabulate

templates = {}

class RemarkableException(Exception):
    pass

class Remarkable:
    templates = {}
    templatefiles = []

    _ssh_client = None
    _sftp_client = None

    REMARKABLE_FOLDERPATH = '/usr/share/remarkable'

    def __init__(self):
        pass

    def connect(self):
        ### code to do the work
        try:
            click.echo("Connecting to reMarkable")
            self._ssh_client = paramiko.SSHClient()
            self._ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            k = paramiko.RSAKey.from_private_key_file('/Users/cmj/.ssh/id_rsa')

            # TODO: config out of file or something
            self._ssh_client.connect('10.11.99.1', username='root', pkey=k)
            click.echo("Connected")
            self._sftp_client = self._ssh_client.open_sftp()
            click.echo("SFTP connection ready")
            self._sftp_client.chdir(self.REMARKABLE_FOLDERPATH)

            self.templatefiles = self._sftp_client.listdir("templates")
            # click.echo("Dirlist: %s" % dirlist)

            click.echo("Retrieving templates.json")
            with self._sftp_client.open("templates/templates.json", "r") as f:
                data = f.read()
            click.echo("Done")

            self.templates = json.loads( data )
            # click.echo( templates.keys() )
            # click.echo( json.dumps( templates['templates'], sort_keys=True, indent=4 ) )

        except Exception as err:
            click.echo(err)
            logging.debug(err)
            logging.info('Error connecting to Host')

            import sys
            sys.exit()

    def checkForExistingTemplate( self, name, basefname ):
        for template in self.templates['templates']:
            # click.echo(template)
            if template['name'] == name:
                raise RemarkableException('Template with name "' + name + '" already exists.')

            if template['filename'] == basefname:
                raise RemarkableException('Template with file name "' + basefname + '" already exists.')

    def checkForExistingTemplateFile(self, templatefile ):
        if templatefile in self.templatefiles:
            raise RemarkableException('Template with file name "' + templatefile + '" already exists on disk.')

    def backupTemplateJSON(self):
        # generate a backup file name
        from datetime import datetime
        backupFile = "templates." + datetime.today().strftime('%Y-%m-%d-%H:%M:%S') + ".json";

        # rename the existing templates.json
        self._sftp_client.rename(self.REMARKABLE_FOLDERPATH + "/templates/templates.json", self.REMARKABLE_FOLDERPATH + "/templates/" + backupFile)

    def saveTemplateJSON(self):
        with self._sftp_client.open(self.REMARKABLE_FOLDERPATH + "/templates/templates.json", mode="w") as f:
            f.write(json.dumps(self.templates, sort_keys=True, indent=4))

    def uploadTemplate(self, filepath, filename, file_noextension, name):
        # upload the file
        self._sftp_client.put(filepath, self.REMARKABLE_FOLDERPATH + "/templates/" + filename)

        # assume it worked
        # TODO: be better

        # add it to the templates
        # TODO: in the future we should grab the existing "Blank" one and adjust it
        self.templates['templates'].extend( [{
            "name": name,
            "filename": file_noextension,
            "iconCode": "\ue9fe",
            "landscape": False,
            "categories": [
                "Life/organize",
                "Custom"
            ],
            "custom": True
        } ] )

        # click.echo( json.dumps( self.templates['templates'], sort_keys=True, indent=4 ) )

        # backup the template.json file just in case
        self.backupTemplateJSON()

        # then write a new one
        self.saveTemplateJSON()

    def removeTemplate( self, filename ):
        click.echo( 'Removing template "%s"' % filename )

        # remove it from the templates in memoru

        toRemove = None
        templates = self.templates['templates']
        for i in range(len(templates)):
            # click.echo( templates[i] )
            if templates[i]['filename'] == filename:
                toRemove = i

        if i == None:
            raise RemarkableException( 'Unable to find template with file name "%s".' % filename )

        fullfilename = None
        # then find the actual full filename (i.e. with extension)
        for i in range(len(remarkable.templatefiles)):
            click.echo( remarkable.templatefiles[i] )
            if remarkable.templatefiles[i].startswith( filename + "." ):
                fullfilename = remarkable.templatefiles[i]

        if not fullfilename:
            raise RemarkableException( "Could not find file on disk" )

        click.echo("About to remove template:")
        click.echo(json.dumps(templates[toRemove], indent=4))

        click.echo()
        click.echo("File name: " + fullfilename)

        if ( not 'custom' in templates[toRemove] ) or (not templates[toRemove]['custom']):
            click.echo("*************************************************")
            click.echo("**                   WARNING                   **")
            click.echo("*************************************************")
            click.echo("*                                               *")
            click.echo("* This does not appear to be a custom template! *")
            click.echo("*                                               *")
            click.echo("*************************************************")

        if not click.confirm('Do you want to continue?'):
            raise RemarkableException( 'Aborting' )

        templates.pop(toRemove)

        self.templates['templates'] = templates

        # backup the template.json file just in case
        self.backupTemplateJSON()

        # save the JSON file
        self.saveTemplateJSON()

        # remove the file itself
        self._sftp_client.remove(self.REMARKABLE_FOLDERPATH + "/templates/" + fullfilename)

    def reboot(self):
        self._ssh_client.exec_command('/sbin/reboot')

remarkable = Remarkable()

remarkable.connect()

@click.group()
def cli():
    pass

###
### Templates
###
@click.group()
def template():
    # click.echo('template')
    pass

@click.command()
@click.argument('filepath', type=click.Path(exists=True))
@click.argument('name', required=False)
def add(filepath,name):
    import os

    filename = os.path.basename(filepath)
    file_noextension = os.path.splitext( filename )[0]
    if not name:
        name = file_noextension

    click.echo("Preparing to add template...")

    click.echo( tabulate( [
        [ "File path", filepath],
        [ "File name", filename  ],
        # [ "No extension" , file_noextension ],
        [ "Template name",  name ]
    ] ) )

    # SANITY CHECK:
    #   does the file or template already exist in the templates.json
    remarkable.checkForExistingTemplate( name, filename )

    from PIL import Image
    # click.echo("Opening file...")
    # click.open_file(filepath, "r")

    # SANITY CHECK:
    #   is it an image
    im = Image.open(filepath)
    click.echo("Image info: %s %s %s %d x %d" % (im.format, im.size, im.mode, im.width, im.height))

    # SANITY CHECK:
    #   image dimensions
    if not ( ( im.height == 1872 ) and ( im.width == 1404 ) ):
        raise RemarkableException( "Image must be 1404 x 1872")

    # SANITY CHECK:
    #   does the file already exist on the reMarkable?
    remarkable.checkForExistingTemplateFile(filename)

    # upload file
    remarkable.uploadTemplate( filepath, filename, file_noextension, name )


@click.command()
@click.argument('filename')
def remove(filename):
    click.echo("remove template")
    remarkable.removeTemplate(filename)

# @click.command()
# def reset():
#     click.echo("reset is not yet implemented")

@click.command()
def list():
    def getRow(row):
        return {
            "Name": row['name'],
            "File name": row['filename'],
            "Orientation": ("Portrait", "Landscape")['landscape' in row and row['landscape'] == True]
        }

    # click.echo( json.dumps( remarkable.templates['templates'], indent=4 ))

    templates = remarkable.templates['templates']
    click.echo_via_pager(tabulate([getRow(templates[i]) for i in range(len(templates))],
                                  headers="keys",
                                  tablefmt="github"))


template.add_command(add)
template.add_command(remove)
# template.add_command(reset)
template.add_command(list)


###
### Screen
###

@click.group()
def screen():
    click.echo('screen')

@click.command()
def reboot():
    click.echo("Rebooting remarkable")
    remarkable.reboot()

cli.add_command(template)
cli.add_command(screen)
cli.add_command(reboot)


if __name__ == '__main__':
    try:
        cli()
    except RemarkableException as e:
        click.echo()
        click.echo( "Error detected: %s" % e.args[0])
