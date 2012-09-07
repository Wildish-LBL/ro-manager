'''
Created on 22-08-2012

@author: piotrhol
'''

import logging
import urllib2
import rdflib
import os

from rocommand import ro_uriutils

log = logging.getLogger(__name__)

ACTION_CREATE_RO = 1
ACTION_RO_EXISTS = 2
ACTION_AGGREGATE_INTERNAL = 3
ACTION_AGGREGATE_EXTERNAL = 4
ACTION_AGGREGATE_ANNOTATION = 5
ACTION_UPDATE_OVERWRITE = 6
ACTION_UPDATE = 7
ACTION_UPDATE_ANNOTATION = 8
ACTION_SKIP = 9
ACTION_DELETE = 10
ACTION_DELETE_ANNOTATION = 11

RESPONSE_YES = 1
RESPONSE_NO = 2

def pushResearchObject(localRo, remoteRo, force = False):
    '''
    Scans a given RO version directory for files that have been modified since last synchronization
    and pushes them to ROSRS. Modification is detected by checking modification times and checksums.
    '''        
    for localResuri in localRo.getAggregatedResources():
        respath = localRo.getComponentUriRel(localResuri)
        if not remoteRo.isAggregatedResource(respath):
            log.debug("ResourceSync.pushResearchObject: %s does was not aggregated in the remote RO"%(respath))
            if localRo.isInternalResource(localResuri):
                log.debug("ResourceSync.pushResearchObject: %s is internal"%(localResuri))
                yield (ACTION_AGGREGATE_INTERNAL, respath)
                filename = ro_uriutils.getFilenameFromUri(localResuri)
                currentChecksum = localRo.calculateChecksum(filename)
                rf = open(filename, 'r')
                (status, reason, headers, resuri) = remoteRo.aggregateResourceInt(
                                         respath, 
                                          localRo.getResourceType(respath), 
                                          rf)
                localRo.getRegistries()[(filename, "etag")] = headers.get("etag", None)
                localRo.getRegistries()[(filename, "checksum")] = currentChecksum
            elif localRo.isExternalResource(localResuri):
                log.debug("ResourceSync.pushResearchObject: %s is external"%(localResuri))
                yield (ACTION_AGGREGATE_EXTERNAL, respath)
                remoteRo.aggregateResourceExt(respath)
            else:
                log.error("ResourceSync.pushResearchObject: %s is neither internal nor external"%(localResuri))
        else:
            log.debug("ResourceSync.pushResearchObject: %s does was already aggregated in the remote RO"%(respath))
            if localRo.isInternalResource(localResuri):
                log.debug("ResourceSync.pushResearchObject: %s is internal"%(localResuri))
                if localRo.isAnnotationNode(respath):
                    # annotations are handled separately
                    pass
                else:
                    log.debug("ResourceSync.pushResearchObject: %s is a resource"%(localResuri))
                    # Get remote ETag
                    (status, reason, headers) = remoteRo.getHead(respath)
                    if status != 200:
                        raise Exception("Error retrieving RO resource", "%03d %s (%s)"%(status, reason, respath))
                    filename = ro_uriutils.getFilenameFromUri(localResuri)
                    currentETag = headers.get("etag", None)
                    currentChecksum = localRo.calculateChecksum(filename)
                    # Check locally stored ETag
                    previousETag = localRo.getRegistries().get((filename, "etag"), None)
                    previousChecksum = localRo.getRegistries().get((filename, "checksum"), None)
                    overwrite = False
                    if not previousETag or previousETag != currentETag:
                        log.debug("ResourceSync.pushResearchObject: %s has been modified in ROSRS"%(respath))
                        yield (ACTION_UPDATE_OVERWRITE, respath)
                        overwrite = True
                    elif not previousChecksum or previousChecksum != currentChecksum:
                        log.debug("ResourceSync.pushResearchObject: %s has been modified locally"%(respath))
                        yield (ACTION_UPDATE, respath)
                        overwrite = True
                    if overwrite:
                        rf = open(ro_uriutils.getFilenameFromUri(localResuri), 'r')
                        (status, reason, headers, resuri) = remoteRo.updateResourceInt(respath, 
                                                   localRo.getResourceType(localResuri),
                                                   rf)
                        localRo.getRegistries()[(filename, "etag")] = headers.get("etag", None)
                        localRo.getRegistries()[(filename, "checksum")] = currentChecksum
                    else:
                        log.debug("ResourceSync.pushResearchObject: %s has NOT been modified"%(respath))
                        yield (ACTION_SKIP, respath)
            elif localRo.isExternalResource(localResuri):
                log.debug("ResourceSync.pushResearchObject: %s is external"%(localResuri))
                yield (ACTION_SKIP, localResuri)
            else:
                log.error("ResourceSync.pushResearchObject: %s is neither internal nor external"%(localResuri))
    
    for resuri in remoteRo.getAggregatedResources():
        respath = remoteRo.getComponentUriRel(resuri)
        if not localRo.isAggregatedResource(respath):
            log.debug("ResourceSync.pushResearchObject: %s will be deaggregated"%(resuri))
            yield (ACTION_DELETE, resuri)
            remoteRo.deaggregateResource(resuri)
        pass            
                
    for (ann_node, ann_body, ann_target) in localRo.getAllAnnotationNodes():
        annpath = localRo.getComponentUriRel(ann_node)
        bodypath = localRo.getComponentUriRel(ann_body)
        targetpath = localRo.getComponentUriRel(ann_target)
        if isinstance(ann_node, rdflib.BNode) or not remoteRo.isAnnotationNode(annpath):
            log.debug("ResourceSync.pushResearchObject: %s is a new annotation"%(annpath))
            (_, _, remote_ann_node_uri) = remoteRo.addAnnotationNode(bodypath, targetpath)
            remote_ann_node_path = remoteRo.getComponentUriRel(remote_ann_node_uri)
            localRo.replaceUri(ann_node, localRo.getComponentUriAbs(remote_ann_node_path))
            yield (ACTION_AGGREGATE_ANNOTATION, remote_ann_node_path)
        else:
            log.debug("ResourceSync.pushResearchObject: %s is an existing annotation"%(annpath))
            remoteRo.updateAnnotationNode(annpath, bodypath, targetpath)
            yield (ACTION_UPDATE_ANNOTATION, ann_node)
            
    for (ann_node, ann_body, ann_target) in remoteRo.getAllAnnotationNodes():
        annpath = remoteRo.getComponentUriRel(ann_node)
        if not localRo.isAnnotationNode(annpath):
            log.debug("ResourceSync.pushResearchObject: annotation %s will be deleted"%(ann_node))
            yield (ACTION_DELETE_ANNOTATION, ann_node)
            remoteRo.deleteAnnotationNode(ann_node)
        pass
    
    localRo.saveRegistries()
    return
    
    
        
