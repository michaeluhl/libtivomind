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

    def by_keyword(self, keyword):
        self.dict['keyword'] = keyword

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

    def by_station_id(self, station_id):
        self.dict['stationId'] = station_id

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

    def __init__(self, session, level_of_detail="medium"):
        self.session = session
        self.level_of_detail = level_of_detail

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

    def _prepare_search(self, search_type, result_type, filt=None, options=None, page_size=20, limit=None):
        payload = filt if filt is not None else {}
        updates = options if options is not None and isinstance(options, dict) else {}
        if isinstance(payload, SearchFilter):
            payload = payload.get_payload()
        if not (payload.keys() | options.keys()) & {'levelOfDetail', 'responseTemplate'}:
            updates['levelOfDetail'] = self.level_of_detail
        payload.update(updates)
        return self._get_paged_response(req_type=search_type,
                                        payload=payload,
                                        target_array=result_type,
                                        page_size=page_size,
                                        limit=limit)

    def channel_search(self):
        return self._prepare_search(search_type='channelSearch',
                                    result_type='channel',
                                    filt=None,
                                    options={'bodyId': self.session.body_id, 'flatten': True, 'noLimit': True},
                                    page_size=25,
                                    limit=None)

    def recording_folder_item_search(self, filt=None, page_size=20, limit=None):
        return self._prepare_search(search_type="recordingFolderItemSearch",
                                    result_type="recordingFolderItem",
                                    filt=filt,
                                    options={'bodyId': self.session.body_id, 'flatten': True},
                                    page_size=page_size,
                                    limit=limit)

    def recording_search(self, filt=None, page_size=20, limit=None):
        return self._prepare_search(search_type="recordingSearch",
                                    result_type="recording",
                                    filt=filt,
                                    options={'bodyId': self.session.body_id, 'state': ['inProgress', 'scheduled']},
                                    page_size=page_size,
                                    limit=limit)

    def offer_search(self, filt=None, page_size=20, limit=None):
        return self._prepare_search(search_type="offerSearch",
                                    result_type="offer",
                                    filt=filt,
                                    options={'bodyId': self.session.body_id},
                                    page_size=page_size,
                                    limit=limit)

    def content_search(self, filt=None, page_size=20, limit=None):
        return self._prepare_search(search_type="contentSearch",
                                    result_type="content",
                                    filt=filt,
                                    options={'bodyId': self.session.body_id},
                                    page_size=page_size,
                                    limit=limit)

    def collection_search(self, filt=None, page_size=20, limit=None):
        return self._prepare_search(search_type="collectionSearch",
                                    result_type="collection",
                                    filt=filt,
                                    options={'bodyId': self.session.body_id, 'omitPgdImages': True},
                                    page_size=page_size,
                                    limit=limit)

    def send_key(self, key):
        self.session.send_request('keyEventSend', {'event': key})
        h, b = self.session.get_response()
        return b


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
