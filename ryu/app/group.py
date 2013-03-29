# Copyright (C) 2011 Nippon Telegraph and Telephone Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
import struct

from ryu.base import app_manager
from ryu.controller import mac_to_port
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_2
from ryu.lib.mac import haddr_to_str


# TODO: we should split the handler into two parts, protocol
# independent and dependant parts.

# TODO: can we use dpkt python library?

# TODO: we need to move the followings to something like db


class Group(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_2.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(Group, self).__init__(*args, **kwargs)
        
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto

        dst, src, _eth_type = struct.unpack_from('!6s6sH', buffer(msg.data), 0)
        dpid = datapath.id

        self.logger.info("packet in dpid:%s srcmac:%s dstmac:%s inport:%s",
                         dpid, haddr_to_str(src), haddr_to_str(dst),
                         msg.match.fields[0].value)
        out_port = ofproto.OFPP_FLOOD

        actions = [datapath.ofproto_parser.OFPActionOutput(out_port,16)]
        
        '''
        len_ = ofproto_v1_2.OFP_BUCKET_SIZE \
            + ofproto_v1_2.OFP_ACTION_GROUP_SIZE
        weight = 4386
        watch_port = 6606
        watch_group = 3

        len_=ofproto.OFP_BUCKET_SIZE, weight=0?, watch_port=None?,watch_group=0001,actions
        '''
        len_ = ofproto_v1_2.OFP_BUCKET_SIZE \
            + ofproto_v1_2.OFP_ACTION_GROUP_SIZE
        weight = 4386
        watch_port = 6606
        watch_group = 3
        group_actions =  datapath.ofproto_parser.OFPBucket(len_,
                         weight,watch_port,
                         watch_group, actions)
        #group_actions.append(actions)
        #16 is the max_len in init(),indicating the total length of this action packet
        group = datapath.ofproto_parser.OFPGroupMod(
            datapath=datapath, command=ofproto.OFPGC_ADD, type_=ofproto.OFPGT_SELECT, 
            group_id=1, buckets=[group_actions])
        
        flow_action = datapath.ofproto_parser.OFPActionGroup(1)
        out = datapath.ofproto_parser.OFPFlowMod(
             datapath,0,0,0,ofproto.OFPFC_ADD,0,0,0xff,0xffffffff,ofproto.OFPP_ANY,1,
             0,datapath.ofproto_parser.OFPMatch(),
             [datapath.ofproto_parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, [flow_action])])
        '''datapath=datapath,cookie=0,cookie_mask=0,table_id=0,command=ofproto.OFPFC_ADD,
        idle_timeout=0,hard_timeout=0,priority=0xff,buffer_id=0xffffffff,
        out_port=ofproto.OFPP_ANY,out_group=0001,flags=0,match=ofproto_parser.OFPMatch(),
        instructions=None'''
        #out = datapath.ofproto_parser.OFPPacketOut(
        #    datapath=datapath, buffer_id=msg.buffer_id, in_port=msg.match.fields[0].value,
        #    actions=actions)
        
        datapath.send_msg(group)
        datapath.send_msg(out)