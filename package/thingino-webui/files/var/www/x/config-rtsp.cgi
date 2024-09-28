#!/bin/haserl
<%in _common.cgi %>
<%
plugin="rtsp"
plugin_name="RTSP/ONVIF Access"
page_title="RTSP/ONVIF Access"

stream0_name="Main stream"
stream1_name="Substream"

prudynt_config=/etc/prudynt.cfg
onvif_config=/etc/onvif.conf
onvif_discovery=/etc/init.d/S96onvif_discovery
onvif_notify=/etc/init.d/S97onvif_notify

rtsp_username=$(awk -F: '/Streaming Service/{print $1}' /etc/passwd)
[ -z "$rtsp_username" ] && rtsp_username=$(awk -F'"' '/username/{print $2}' $prudynt_config)
[ -z "$rtsp_password" ] && rtsp_password=$(awk -F'"' '/password/{print $2}' $prudynt_config)
[ -z "$rtsp_password" ] && rtsp_password="thingino"

if [ "POST" = "$REQUEST_METHOD" ]; then
	rtsp_password=$POST_rtsp_password
	sanitize rtsp_password

	if [ -z "$error" ]; then
		tmpfile=$(mktemp)
		cat $onvif_config > $tmpfile
		#sed -i "/^user=/cuser=$rtsp_username" $tmpfile
		sed -i "/^password=/cpassword=$rtsp_password" $tmpfile
		mv $tmpfile $onvif_config

		prudyntcfg set rtsp.password "\"$rtsp_password\""

		echo "$rtsp_username:$rtsp_password" | chpasswd -c sha512

		if [ -f "$onvif_discovery" ]; then
			$onvif_discovery restart >> /tmp/webui.log
		else
			echo "$onvif_discovery not found" >> /tmp/webui.log
		fi

		if [ -f "$onvif_notify" ]; then
			$onvif_notify restart >> /tmp/webui.log
		else
			echo "$onvif_notify not found" >> /tmp/webui.log
		fi

		update_caminfo
		redirect_to $SCRIPT_NAME
	fi
fi
%>
<%in _header.cgi %>

<div class="row row-cols-1 row-cols-md-2 row-cols-xl-3 g-4">
<div class="col">
<h3>Access</h3>
<form action="<%= $SCRIPT_NAME %>" method="post">
<% field_text "rtsp_username" "RTSP/ONVIF Username" %>
<% field_password "rtsp_password" "RTSP/ONVIF Password" %>
<% button_submit %>
</form>
</div>
<%
for i in 0 1; do
	domain="stream$i"
%>
<div class="col">
<h3><% eval echo \$${domain}_name %></h3>
<% field_switch "${domain}_enabled" "Enabled" %>
<div class="row g-2">
<div class="col-3"><% field_text "${domain}_width" "Width" %></div>
<div class="col-3"><% field_text "${domain}_height" "Height" %></div>
<div class="col-6"><% field_range "${domain}_fps" "FPS" "15,30,1" %></div>
</div>
<div class="row g-2">
<div class="col"><% field_select "${domain}_format" "Format" "H264,H265" %></div>
<div class="col"><% field_text "${domain}_bitrate" "Bitrate" %></div>
<div class="col"><% field_text "${domain}_mode" "Mode" %></div>
</div>
<div class="row g-2">
<div class="col"><% field_text "${domain}_buffers" "Buffers" %></div>
<div class="col"><% field_text "${domain}_gop" "GOP" %></div>
<div class="col"><% field_text "${domain}_max_gop" "Max. GOP" %></div>
<div class="col"><% field_text "${domain}_profile" "Profile" %></div>
</div>
<div class="row g-2">
<div class="col-9"><% field_text "${domain}_rtsp_endpoint" "Endpoint" "rtsp://$rtsp_username:$rtsp_password@$network_address/ch0" %></div>
<div class="col-3"><% field_text "${domain}_rotation" "Rotation" %></div>
</div>
<% field_switch "${domain}_audio_enabled" "Audio" %>
</div>
<% done %>
</div>

<pre class="mt-4">
onvif://<%= $rtsp_username %>:<%= $rtsp_password %>@<%= $network_address %>/onvif/device_service
</pre>

<script>
const STREAM0_THREAD = 0;
const STREAM1_THREAD = 1;

const params = ['audio_enabled', 'bitrate', 'buffers', 'enabled', 'format', 'fps', 'gop',
	'height', 'max_gop', 'mode', 'profile', 'rotation', 'rtsp_endpoint', 'width'];

let ws = new WebSocket('ws://' + document.location.hostname + ':8089?token=<%= $ws_token %>');
ws.onopen = () => {
	console.log('WebSocket connection opened');
	stream_rq = '{' + params.map((x) => `"${x}":null`).join() + '}';
	const payload = '{"stream0":' + stream_rq + ',"stream1":' + stream_rq + '}';
	console.log(payload);
	ws.send(payload);
}
ws.onclose = () => { console.log('WebSocket connection closed'); }
ws.onerror = (error) => { console.error('WebSocket error', error); }
ws.onmessage = (event) => {
	if (event.data == '') {
		console.log('empty response');
		return;
	} else {
		console.log(ts(), '<===', event.data);
	}
	const msg = JSON.parse(event.data);
	const time = new Date(msg.date);
	const timeStr = time.toLocaleTimeString();
	let data;
<%
for i in 0 1; do
	stream="stream$i"
%>
	data = msg.<%= $stream %>;
	if (data)
		params.forEach(x => setValue(data, '<%= $stream %>', x));
<% done %>
}

const andSave = ',"action":{"save_config":null,"restart_thread":' + ThreadVideo + '}'

function sendToWs(payload) {
	payload = payload.replace(/}$/, andSave + '}')
	console.log(ts(), '===>', payload);
	ws.send(payload);
}

function setValue(data, domain, name) {
	const id = `#${domain}_${name}`;
	const el = $(id);
	const value = data[name];
	if (el.type == "checkbox") {
		el.checked = value;
	} else {
		if (el && value) el.value = value;
		if (el.type == "range") $(`${id}-show`).value = value;
	}
}

$('#rtsp_username').readOnly = true;
</script>

<%in _footer.cgi %>
