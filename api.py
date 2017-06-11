import copy
import contextlib
import threading

import tivotalk.mind.rpc as rpc


class SearchFilter(object):

    def __init__(self):
        self.dict = {}

    def by_keywordable(self, field, value, exact_match=False):
        key = field
        if not exact_match:
            key += "Keyword"
        self.dict[key] = value

    def by_title(self, title, exact_match=False):
        self.by_keywordable('title', title, exact_match)

    def by_subtitle(self, subtitle, exact_match=False):
        self.by_keywordable('subtitle', subtitle, exact_match)

    def by_description(self, description, exact_match=False):
        self.by_keywordable('description', description, exact_match)

    def by_credit(self, credit, exact_match=False):
        self.by_keywordable('credit', credit, exact_match)

    def by_start_time(self, min_utc_time=None, max_utc_time=None):
        if min_utc_time:
            self.dict['minStartTime'] = rpc.MRPCSession.get_date_string(min_utc_time)
        if max_utc_time:
            self.dict['maxStartTime'] = rpc.MRPCSession.get_date_string(max_utc_time)

    def by_end_time(self, min_utc_time=None, max_utc_time=None):
        if min_utc_time:
            self.dict['minEndTime'] = rpc.MRPCSession.get_date_string(min_utc_time)
        if max_utc_time:
            self.dict['maxEndTime'] = rpc.MRPCSession.get_date_string(max_utc_time)

    def by_content_id(self, content_id):
        if isinstance(content_id, dict):
            content_id = content_id['contentId']
        self.dict['contentId'] = content_id

    def by_collection_id(self, collection_id):
        if isinstance(collection_id, dict):
            collection_id = collection_id['collectionId']
        self.dict['collectionId'] = collection_id

    def order_by(self, sort_field):
        self.dict['orderBy'] = sort_field

    def set_level_of_detail(self, level_of_detail=None):
        if level_of_detail is None:
            try:
                del self.dict['levelOfDetail']
            except KeyError:
                pass
        elif 'responseTemplate' in self.dict:
            raise ValueError('level_of_detail and response_template are conflicting options.  Clear response '
                             'templates before setting level of detail.')
        else:
            self.dict['levelOfDetail'] = level_of_detail

    def set_response_template(self, template_list=None):
        if template_list is None:
            try:
                del self.dict['responseTemplate']
            except KeyError:
                pass
        elif 'levelOfDetail' in self.dict:
            raise ValueError('level_of_detail and response_template are conflicting options.  Clear level of '
                             'detail before setting response templates.')
        else:
            self.dict['responseTemplate'] = template_list[:]

    def pop(self, key, *args):
        return self.dict.pop(key, *args)

    def setdefault(self, key, default=None):
        return self.dict.setdefault(key, default)

    def get_payload(self):
        return copy.copy(self.dict)


class Mind(object):

    def __init__(self, session):
        self.session = session

    def _get_paged_response(self, req_type, payload, target_array, page_size=20, limit=None):
        results = []
        payload['count'] = page_size
        self.session.send_request(req_type, payload)
        h, b = self.session.get_response()
        while target_array in b and len(b[target_array]) > 0:
            results.extend(b[target_array])
            if (limit is not None and len(results) > limit) or ('isBottom' in b and b['isBottom']):
                break
            if 'count' in payload:
                del payload['count']
            payload['offset'] = len(results)
            self.session.send_request(req_type, payload)
            h, b = self.session.get_response()
        return results

    def recording_folder_item_search(self, filt=None, level_of_detail="medium", limit=None):
        payload = filt if filt is not None else {}
        if isinstance(payload, SearchFilter):
            payload = payload.get_payload()
        payload.update({'bodyId': self.session.body_id,
                        'levelOfDetail': level_of_detail,
                        'flatten': True})
        return self._get_paged_response("recordingFolderItemSearch", payload, "recordingFolderItem", 20, limit=limit)

    def recording_search(self, filt=None, level_of_detail="medium", limit=None):
        payload = filt if filt is not None else {}
        if isinstance(payload, SearchFilter):
            payload = payload.get_payload()
        payload.update({'bodyId': self.session.body_id,
                        'levelOfDetail': level_of_detail,
                        'state': ['inProgress', 'scheduled']})
        return self._get_paged_response("recordingSearch", payload, "recording", 20, limit=limit)

    def offer_search(self, filt=None, level_of_detail="medium", limit=None):
        payload = filt if filt is not None else {}
        if isinstance(payload, SearchFilter):
            payload = payload.get_payload()
        payload['bodyId'] = self.session.body_id
        payload['levelOfDetail'] = level_of_detail
        return self._get_paged_response("offerSearch", payload, "offer", 20, limit=limit)

    def content_search(self, filt=None, level_of_detail="medium", limit=None):
        payload = filt if filt is not None else {}
        if isinstance(payload, SearchFilter):
            payload = payload.get_payload()
        payload['bodyId'] = self.session.body_id
        payload['levelOfDetail'] = level_of_detail
        return self._get_paged_response("contentSearch", payload, "content", 20, limit=limit)

    def collection_search(self, filt=None, level_of_detail="medium", limit=None):
        payload = filt if filt is not None else {}
        if isinstance(payload, SearchFilter):
            payload = payload.get_payload()
        payload['bodyId'] = self.session.body_id
        payload['levelOfDetail'] = level_of_detail
        payload['omitPgdImages'] = True
        return self._get_paged_response("collectionSearch", payload, "collection", 20, limit=limit)

    @staticmethod
    def new_session(cert_path, cert_password, address, credential, port=1413, debug=False):
        mrpc = rpc.MRPCSession.new_session(cert_path=cert_path,
                                           cert_password=cert_password,
                                           address=address,
                                           credential=credential,
                                           port=port,
                                           debug=debug)
        mrpc.connect()
        return Mind(session=mrpc)

    @staticmethod
    def new_local_session(cert_path, cert_password, address, mak, port=1413, debug=False):
        mrpc = rpc.MRPCSession.new_local_session(cert_path=cert_path,
                                                 cert_password=cert_password,
                                                 address=address,
                                                 mak=mak,
                                                 port=port,
                                                 debug=debug)
        mrpc.connect()
        return Mind(session=mrpc)


class MindManager(object):

    def __init__(self, cert_path, cert_password, address, credential,
                 port=1413, debug=False, timeout=120):
        self.__cert_path = cert_path
        self.__cert_password = cert_password
        self.__address = address
        self.__credential = credential
        self.__port = port
        self.__debug = debug
        self.__timeout = timeout
        self.__mind = None
        self.__timer = None
        pass

    def disconnect(self):
        try:
            self.__mind.session.close()
        except AttributeError:
            pass
        finally:
            self.__mind = None
        if threading.current_thread().getName() == threading.main_thread().getName():
            try:
                self.__timer.cancel()
            except AttributeError:
                pass
            finally:
                self.__timer = None

    @contextlib.contextmanager
    def mind(self):
        if self.__timer is not None:
            self.__timer.cancel()
            self.__timer = None
        if self.__mind is None:
            self.__mind = Mind.new_session(cert_path=self.__cert_path,
                                           cert_password=self.__cert_password,
                                           address=self.__address,
                                           credential=self.__credential,
                                           port=self.__port,
                                           debug=self.__debug)
        yield self.__mind
        self.__timer = threading.Timer(self.__timeout, self.disconnect)
