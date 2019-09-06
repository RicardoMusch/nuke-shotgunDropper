import nuke
import os
import re
import sg_connection
#from shotgun_api3 import Shotgun

import sgtk
# get the engine we are currently running in
current_engine = sgtk.platform.current_engine()
# get hold of the shotgun api instance used by the engine, (or we could have created a new one)
shotgun = current_engine.shotgun

# This is simple example for how to use Nuke's dropdata callback to communicate with Shotgun.
# and bring Shotgun Versions into Nuke simply by dragging them out of the browser and into Nuke.
#
# Customise the shotgun query and subsequent Nuke command in the dropSGVersion function to
# make this work with your particular Shotgun setup and/or to extend the functionality of this script.

def getLocalPath():
    '''Return a path to download quicktimes to'''
    return os.environ['NUKE_TEMP_DIR']

def getVersions (connection, link, ignore=None):
    '''Return all versions that are linked to a shotgun entity (eg shot or asset etc).
    args:
        link	-	shotgun entity to search for versions (i.e. {'type':'Shot', 'id':1226} )
        ignore  -   list of status' to ignore (eg ['omt', 'clsd', 'hold']). If None, all versions are returned regardless of their status.'''
    columns = [ 'code', 'sg_status_list', 'sg_version_type', 'sg_path_to_frames', 'sg_first_frame', 'sg_last_frame' ]
    filters = [ ['entity', 'is', link] ]
    versions = connection.find( 'Version', filters, columns )
    if not ignore:
        return versions
    return [ v for v in versions if v['sg_status_list'] not in ignore ]

def getPlaylistVersionsByID (connection, playlist):
        '''return a playlist's content
        args:
            playlist  -  requested playlist id'''
        columns = [ 'sg_path_to_frames', 'sg_path_to_movie', 'sg_first_frame', 'sg_last_frame' ]
        print playlist
        filters = [ ['playlists', 'is', {'type':'Playlist', 'id':int(playlist)} ] ]
        result = connection.find('Version', filters, columns)
        return result

def dropSG(mimeType, text):
    '''Parse the received url for the ID, connect to shotgun and retrieve info for the particular ID.
    args:
       text  -  url of a shotgun version'''
    # DO SOME MORE CHECKING IF WE CARE ABOUT THIS PARTICULAR URL.
    # THIS PARTICULAR SCRIPT ONLY CARES ABOUT VERSIONS

    if not mimeType == 'text/plain' or not (text.startswith( 'http' ) and 'shotgunstudio' in text):
        return False
        
    def idCheck(url, sgType):
        foundID = re.match( '.+%s/(\d+)' % sgType, url )
        foundIDinEmail = re.match( '.+entity_id=(\d+).+entity_type=%s' % sgType, url )
        foundIDinURL = re.match( r'.+#%s_(\d+)_' % sgType, url )
        if not foundID and not foundIDinEmail and not foundIDinURL:
            return
        try:
            if foundID:
                return int( foundID.group(1) )
            elif foundIDinEmail:
                return int( foundIDinEmail.group(1) )
            elif foundIDinURL:
                return int( foundIDinURL.group(1) )
        except ValueError:
            return

    SERVER_PATH = os.environ["SERVER_PATH"]
    SCRIPT_NAME = os.environ["SCRIPT_NAME"]
    SCRIPT_KEY = os.environ["SCRIPT_KEY"]
    
    #-------------------------------- VERSION
    if 'Version' in text:
        sgID = idCheck(text, 'Version')
        print 'retrieving shotgun version %s' % sgID
        #DO THE SHOTGUN THING
        CONNECT = shotgun
        # QUERY SHOTGUN FOR THE FOUND ID
        columns = ['sg_path_to_frames', 'sg_first_frame', 'sg_last_frame']
        filters = [ [ 'id', 'is', sgID] ]
        v = shotgun.find_one( 'Version', filters, columns )
        if v['sg_path_to_frames']:
            #print v
            # DO THE NUKE THING WITH THE FOUND PATH ON THE LOCAL SERVER
            r = nuke.nodes.Read()
            path = v.get("sg_path_to_frames")
            path = path.replace("\\","/")
            #print path
            r["file"].setValue(path)
            r["first"].setValue(v.get("sg_first_frame"))
            r["last"].setValue(v.get("sg_last_frame"))
            r["origfirst"].setValue(v.get("sg_first_frame"))
            r["origlast"].setValue(v.get("sg_last_frame"))
            #nuke.createNode('Read', 'file %(sg_path_to_frames)s first %(sg_first_frame)s last %(sg_last_frame)s origfirst %(sg_first_frame)s origlast %(sg_last_frame)s' % v)
        else:
            # download the version file if the local path is empty
            version_ent = shotgun.find_one('Version', [['id', 'is', sgID]], ['sg_uploaded_movie'])
            version_mov = version_ent['sg_uploaded_movie']
            version_name = version_mov['name']
            version_url = version_mov['url']
            local_path = os.path.join(getLocalPath(), version_name)
            shotgun.download_attachment(attachment=version_ent['sg_uploaded_movie'], file_path=local_path)            
            nuke.createNode('Read', 'file {}'.format(local_path))

        return True
    #-------------------------------- PLAYLIST
    elif 'Playlist' in text:
        sgID = idCheck( text, 'Playlist' )
        print 'retrieving shotgun playlist %s' % sgID
        #DO THE SHOTGUN THING
        CONNECT = shotgun
        versions = getPlaylistVersionsByID( CONNECT, sgID )

        #DO THE NUKE THING
        for v in versions:
            r = nuke.nodes.Read()
            path = v.get("sg_path_to_frames")
            path = path.replace("\\","/")
            #print path
            r["file"].setValue(path)
            r["first"].setValue(v.get("sg_first_frame"))
            r["last"].setValue(v.get("sg_last_frame"))
            r["origfirst"].setValue(v.get("sg_first_frame"))
            r["origlast"].setValue(v.get("sg_last_frame"))
            #nuke.createNode( 'Read', 'file %(sg_path_to_frames)s first %(sg_first_frame)s last %(sg_last_frame)s origfirst %(sg_first_frame)s origlast %(sg_last_frame)s' % v )
        return True        
    #-------------------------------- SHOT
    elif 'Shot' in text:
        sgID = idCheck( text, 'Shot' )        
        print 'retrieving shotgun shot %s' % sgID
        #DO THE SHOTGUN THING
        CONNECT = shotgun
        versions = getVersions( CONNECT, {'type':'Shot', 'id':int(sgID)}, ignore=['omt'] )
        # GET SHOT DESCRIPTION
        columns = ['description']
        filters = [ [ 'id', 'is', sgID] ]
        shot = shotgun.find_one( 'Shot', filters, columns )
        desc = shot['description']
        #DO THE NUKE THING
        for v in versions:
            r = nuke.nodes.Read()
            path = v.get("sg_path_to_frames")
            path = path.replace("\\","/")
            #print path
            r["file"].setValue(path)
            r["first"].setValue(v.get("sg_first_frame"))
            r["last"].setValue(v.get("sg_last_frame"))
            r["origfirst"].setValue(v.get("sg_first_frame"))
            r["origlast"].setValue(v.get("sg_last_frame"))
            r["label"].setValue(v.get("sg_version_type"))
            #nuke.createNode( 'Read', 'file %(sg_path_to_frames)s first %(sg_first_frame)s last %(sg_last_frame)s origfirst %(sg_first_frame)s origlast %(sg_last_frame)s label %(sg_version_type)s' % v )

        if desc:
            nuke.createNode( 'StickyNote', 'label "%s"' % desc )

        return True
    
    else:
        return False