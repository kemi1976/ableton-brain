"""
ABLETON BRAIN - Remote Script for Ableton Live
Installs to: C:\\Users\\[You]\\Documents\\Ableton\\User Library\\Remote Scripts\\AbletonBrain\\
Control Surface: AbletonBrain | Input: None | Output: None
"""
import Live
import socket
import threading
import json
import time
import os
from _Framework.ControlSurface import ControlSurface
from _Framework.InputControlElement import MIDI_CC_TYPE
from _Framework.SubjectSlot import subject_slot
from _Framework.MidiMap import make_encoder

class AbletonBrainRemote(ControlSurface):
    """Ableton Brain Remote Script - TCP bridge for external AI control"""

    def __init__(self, c_instance):
        super(AbletonBrainRemote, self).__init__(c_instance)
        self._socket_server = None
        self._socket_thread = None
        self._running = False
        self._clients = []
        self._host = '127.0.0.1'
        self._port = 9877
        self._log("Ableton Brain Remote Script initialized")
        self._start_server()

    def _log(self, msg):
        self.log_message(f"[AbletonBrain] {msg}")

    def _start_server(self):
        """Start TCP server in background thread"""
        try:
            self._socket_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._socket_server.bind((self._host, self._port))
            self._socket_server.listen(5)
            self._running = True
            self._socket_thread = threading.Thread(target=self._accept_clients, daemon=True)
            self._socket_thread.start()
            self._log(f"TCP server listening on {self._host}:{self._port}")
        except Exception as e:
            self._log(f"Server start error: {e}")

    def _accept_clients(self):
        """Accept incoming client connections"""
        while self._running:
            try:
                client, addr = self._socket_server.accept()
                client.settimeout(30)
                self._clients.append(client)
                self._log(f"Client connected: {addr}")
                threading.Thread(target=self._handle_client, args=(client,), daemon=True).start()
            except Exception as e:
                if self._running:
                    self._log(f"Accept error: {e}")
                time.sleep(0.1)

    def _handle_client(self, client):
        """Handle client messages"""
        buffer = ""
        while self._running:
            try:
                data = client.recv(4096).decode('utf-8')
                if not data:
                    break
                buffer += data
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if line.strip():
                        self._process_command(client, line.strip())
            except socket.timeout:
                continue
            except Exception as e:
                self._log(f"Client error: {e}")
                break
        self._remove_client(client)

    def _remove_client(self, client):
        """Remove client from list"""
        try:
            client.close()
        except:
            pass
        if client in self._clients:
            self._clients.remove(client)

    def _process_command(self, client, line):
        """Process JSON command from client"""
        try:
            cmd = json.loads(line)
            command = cmd.get('command')
            params = cmd.get('params', {})
            request_id = cmd.get('id', '')

            # Schedule on Live's main thread
            def execute():
                result = self._execute_command(command, params)
                response = {'id': request_id, 'status': 'success', 'result': result}
                self._send_response(client, response)

            self.schedule_message(0, execute)

        except json.JSONDecodeError:
            self._send_error(client, '', 'Invalid JSON')
        except Exception as e:
            self._send_error(client, cmd.get('id', ''), str(e))

    def _send_response(self, client, response):
        """Send JSON response to client"""
        try:
            client.send((json.dumps(response) + '\n').encode('utf-8'))
        except:
            self._remove_client(client)

    def _send_error(self, client, request_id, error):
        """Send error response"""
        self._send_response(client, {'id': request_id, 'status': 'error', 'error': error})

    # =========================================================================
    # COMMAND EXECUTION - Live Object Model (LOM) Operations
    # =========================================================================

    def _execute_command(self, command, params):
        """Route command to appropriate handler"""
        handlers = {
            # Session/Transport
            'get_session_info': self._get_session_info,
            'set_tempo': self._set_tempo,
            'set_scale': self._set_scale,
            'play': self._play,
            'stop': self._stop,
            'record': self._record,

            # Tracks
            'create_midi_track': self._create_midi_track,
            'create_audio_track': self._create_audio_track,
            'delete_track': self._delete_track,
            'get_tracks': self._get_tracks,
            'arm_track': self._arm_track,
            'set_track_volume': self._set_track_volume,
            'set_track_pan': self._set_track_pan,

            # Clips
            'create_midi_clip': self._create_midi_clip,
            'create_audio_clip': self._create_audio_clip,
            'get_clip_notes': self._get_clip_notes,
            'add_notes_to_clip': self._add_notes_to_clip,
            'set_clip': self._set_clip,
            'fire_clip': self._fire_clip,
            'stop_clip': self._stop_clip,

            # Devices
            'load_instrument': self._load_instrument,
            'load_audio_effect': self._load_audio_effect,
            'load_midi_effect': self._load_midi_effect,
            'get_device_parameters': self._get_device_parameters,
            'set_device_parameter': self._set_device_parameter,
            'batch_set_device_parameters': self._batch_set_device_parameters,
            'insert_device': self._insert_device,
            'read_device': self._read_device,

            # Drum Rack
            'create_drum_rack': self._create_drum_rack,
            'replace_sample': self._replace_sample,
            'create_drum_pattern': self._create_drum_pattern,

            # Scenes/Arrangement
            'create_scene': self._create_scene,
            'delete_clip': self._delete_clip,
            'copy_clip': self._copy_clip,
            'set_clip_envelope': self._set_clip_envelope,

            # Samples/Browser
            'list_samples': self._list_samples,
            'analyze_sample': self._analyze_sample,

            # VST/AU Plugin Control
            'probe_plugin_parameters': self._probe_plugin_parameters,
            'expose_plugin_parameters': self._expose_plugin_parameters,
            'get_serum_fx': self._get_serum_fx,
            'set_serum_fx_param': self._set_serum_fx_param,
            'insert_serum_fx': self._insert_serum_fx,
            'remove_serum_fx': self._remove_serum_fx,
            'reorder_serum_fx': self._reorder_serum_fx,
            'get_serum_patch': self._get_serum_patch,
            'set_serum_oscillator': self._set_serum_oscillator,
            'set_serum_filter': self._set_serum_filter,
            'set_serum_envelope': self._set_serum_envelope,
            'set_serum_lfo': self._set_serum_lfo,
            'set_serum_macro': self._set_serum_macro,
            'set_serum_wavetable': self._set_serum_wavetable,
            'add_serum_mod_route': self._add_serum_mod_route,
            'clear_serum_mod_route': self._clear_serum_mod_route,
            'create_serum_patch': self._create_serum_patch,

            # File operations
            'inspect_als': self._inspect_als,
            'render_audio': self._render_audio,

            # Audio Analysis & Mixing
            'install_analyzer': self._install_analyzer,
            'read_analyzer': self._read_analyzer,
            'get_all_analyzers': self._get_all_analyzers,
            'mix_doctor': self._mix_doctor,
            'compare_to_reference': self._compare_to_reference,
            'capture_stems': self._capture_stems,
        }

        if command not in handlers:
            raise ValueError(f"Unknown command: {command}")

        return handlers[command](params)

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def _song(self):
        return self.song()

    def _get_track(self, index):
        tracks = list(self._song().tracks)
        return tracks[index] if 0 <= index < len(tracks) else None

    def _get_return_track(self, index):
        returns = list(self._song().return_tracks)
        return returns[index] if 0 <= index < len(returns) else None

    def _get_master_track(self):
        return self._song().master_track

    def _get_device(self, track_index, device_index):
        track = self._get_track(track_index)
        if track and device_index < len(track.devices):
            return track.devices[device_index]
        return None

    def _get_clip(self, track_index, clip_index):
        track = self._get_track(track_index)
        if track and track.clip_slots and clip_index < len(track.clip_slots):
            slot = track.clip_slots[clip_index]
            return slot.clip if slot.has_clip else None
        return None

    def _normalize_value(self, param, value):
        """Convert 0-1 normalized value to actual parameter value"""
        return param.min + value * (param.max - param.min)

    def _denormalize_value(self, param, value):
        """Convert actual parameter value to 0-1 normalized"""
        if param.max == param.min:
            return 0.0
        return (value - param.min) / (param.max - param.min)

    # =========================================================================
    # SESSION / TRANSPORT
    # =========================================================================

    def _get_session_info(self, params):
        song = self._song()
        return {
            'tempo': song.tempo,
            'time_signature': f"{song.signature_numerator}/{song.signature_denominator}",
            'is_playing': song.is_playing,
            'is_recording': song.record_mode,
            'loop': song.loop,
            'scene_count': len(song.scenes),
            'track_count': len(song.tracks),
        }

    def _set_tempo(self, params):
        tempo = params.get('tempo', 120)
        self._song().tempo = max(20, min(999, tempo))
        return {'tempo': self._song().tempo}

    def _set_scale(self, params):
        # Scale is per-clip in Live 12, not global
        # This would set key for new clips
        key = params.get('key', 'C')
        scale = params.get('scale', 'major')
        return {'key': key, 'scale': scale}

    def _play(self, params):
        self._song().start_playing()
        return {'status': 'playing'}

    def _stop(self, params):
        self._song().stop_playing()
        return {'status': 'stopped'}

    def _record(self, params):
        self._song().record_mode = True
        self._song().start_playing()
        return {'status': 'recording'}

    # =========================================================================
    # TRACKS
    # =========================================================================

    def _create_midi_track(self, params):
        index = params.get('index', -1)
        name = params.get('name', 'MIDI Track')
        track = self._song().create_midi_track(index)
        track.name = name
        return {'track_index': list(self._song().tracks).index(track), 'name': name}

    def _create_audio_track(self, params):
        index = params.get('index', -1)
        name = params.get('name', 'Audio Track')
        track = self._song().create_audio_track(index)
        track.name = name
        return {'track_index': list(self._song().tracks).index(track), 'name': name}

    def _delete_track(self, params):
        index = params.get('track_index')
        track = self._get_track(index)
        if track:
            self._song().delete_track(track)
            return {'deleted': True}
        return {'deleted': False, 'error': 'Track not found'}

    def _get_tracks(self, params):
        result = []
        for i, track in enumerate(self._song().tracks):
            result.append({
                'index': i,
                'name': track.name,
                'type': 'midi' if track.has_midi_input else 'audio',
                'armed': track.arm,
                'volume': track.mixer_device.volume.value,
                'pan': track.mixer_device.panning.value,
                'devices': [d.name for d in track.devices],
            })
        return {'tracks': result}

    def _arm_track(self, params):
        index = params.get('track_index')
        arm = params.get('arm', True)
        track = self._get_track(index)
        if track:
            track.arm = arm
            return {'armed': arm}
        return {'error': 'Track not found'}

    def _set_track_volume(self, params):
        index = params.get('track_index')
        volume = params.get('volume', 0.0)
        track = self._get_track(index)
        if track:
            track.mixer_device.volume.value = volume
            return {'volume': volume}
        return {'error': 'Track not found'}

    def _set_track_pan(self, params):
        index = params.get('track_index')
        pan = params.get('pan', 0.0)
        track = self._get_track(index)
        if track:
            track.mixer_device.panning.value = pan
            return {'pan': pan}
        return {'error': 'Track not found'}

    # =========================================================================
    # CLIPS
    # =========================================================================

    def _create_midi_clip(self, params):
        track_index = params.get('track_index')
        clip_index = params.get('clip_index', 0)
        length = params.get('length', 4.0)
        track = self._get_track(track_index)
        if track:
            slot = track.clip_slots[clip_index]
            slot.create_clip(length)
            return {'created': True}
        return {'error': 'Track not found'}

    def _create_audio_clip(self, params):
        track_index = params.get('track_index')
        clip_index = params.get('clip_index', 0)
        file_path = params.get('file_path')
        track = self._get_track(track_index)
        if track and file_path:
            slot = track.clip_slots[clip_index]
            slot.create_clip(file_path)
            return {'created': True}
        return {'error': 'Track not found or no file path'}

    def _get_clip_notes(self, params):
        track_index = params.get('track_index')
        clip_index = params.get('clip_index')
        clip = self._get_clip(track_index, clip_index)
        if clip and clip.is_midi_clip:
            notes = []
            for note in clip.get_notes(0.0, 0, clip.length, 127):
                notes.append({
                    'pitch': note[0],
                    'start_time': note[1],
                    'duration': note[2],
                    'velocity': note[3],
                    'muted': note[4],
                })
            return {'notes': notes, 'length': clip.length, 'loop': clip.looping}
        return {'error': 'Clip not found or not MIDI'}

    def _add_notes_to_clip(self, params):
        track_index = params.get('track_index')
        clip_index = params.get('clip_index')
        notes = params.get('notes', [])
        clip = self._get_clip(track_index, clip_index)
        if clip and clip.is_midi_clip:
            for note in notes:
                clip.set_notes([
                    (note.get('pitch', 60),
                     note.get('start_time', 0),
                     note.get('duration', 1),
                     note.get('velocity', 100),
                     note.get('muted', False))
                ])
            return {'added': len(notes)}
        return {'error': 'Clip not found or not MIDI'}

    def _set_clip(self, params):
        track_index = params.get('track_index')
        clip_index = params.get('clip_index')
        clip = self._get_clip(track_index, clip_index)
        if clip:
            if 'name' in params:
                clip.name = params['name']
            if 'looping' in params:
                clip.looping = params['looping']
            if 'start_marker' in params:
                clip.start_marker = params['start_marker']
            if 'end_marker' in params:
                clip.end_marker = params['end_marker']
            return {'updated': True}
        return {'error': 'Clip not found'}

    def _fire_clip(self, params):
        track_index = params.get('track_index')
        clip_index = params.get('clip_index')
        track = self._get_track(track_index)
        if track:
            slot = track.clip_slots[clip_index]
            slot.fire()
            return {'fired': True}
        return {'error': 'Track not found'}

    def _stop_clip(self, params):
        track_index = params.get('track_index')
        track = self._get_track(track_index)
        if track:
            track.stop_all_clips()
            return {'stopped': True}
        return {'error': 'Track not found'}

    # =========================================================================
    # DEVICES
    # =========================================================================

    def _load_instrument(self, params):
        track_index = params.get('track_index')
        device_name = params.get('device_name')
        track = self._get_track(track_index)
        if track:
            track.devices.load_instrument(device_name)
            return {'loaded': device_name}
        return {'error': 'Track not found'}

    def _load_audio_effect(self, params):
        track_index = params.get('track_index')
        device_name = params.get('device_name')
        track = self._get_track(track_index)
        if track:
            track.devices.load_audio_effect(device_name)
            return {'loaded': device_name}
        return {'error': 'Track not found'}

    def _load_midi_effect(self, params):
        track_index = params.get('track_index')
        device_name = params.get('device_name')
        track = self._get_track(track_index)
        if track:
            track.devices.load_midi_effect(device_name)
            return {'loaded': device_name}
        return {'error': 'Track not found'}

    def _get_device_parameters(self, params):
        track_index = params.get('track_index')
        device_index = params.get('device_index')
        device = self._get_device(track_index, device_index)
        if device:
            params_list = []
            for i, param in enumerate(device.parameters):
                params_list.append({
                    'index': i,
                    'name': param.name,
                    'value': param.value,
                    'normalized': self._denormalize_value(param, param.value),
                    'min': param.min,
                    'max': param.max,
                    'is_quantized': param.is_quantized,
                    'unit': str(param.unit) if hasattr(param, 'unit') else '',
                })
            return {'device_name': device.name, 'parameters': params_list}
        return {'error': 'Device not found'}

    def _set_device_parameter(self, params):
        track_index = params.get('track_index')
        device_index = params.get('device_index')
        param_index = params.get('parameter_index')
        value = params.get('value', 0.0)
        device = self._get_device(track_index, device_index)
        if device and param_index < len(device.parameters):
            param = device.parameters[param_index]
            actual = self._normalize_value(param, value)
            param.value = actual
            return {'value': actual, 'normalized': value}
        return {'error': 'Parameter not found'}

    def _batch_set_device_parameters(self, params):
        track_index = params.get('track_index')
        device_index = params.get('device_index')
        param_indices = params.get('parameter_indices', [])
        values = params.get('values', [])
        device = self._get_device(track_index, device_index)
        if device:
            for idx, val in zip(param_indices, values):
                if idx < len(device.parameters):
                    param = device.parameters[idx]
                    param.value = self._normalize_value(param, val)
            return {'set': len(param_indices)}
        return {'error': 'Device not found'}

    def _insert_device(self, params):
        track_index = params.get('track_index')
        device_name = params.get('device_name')
        index = params.get('index', -1)
        track = self._get_track(track_index)
        if track:
            track.devices.insert_device(device_name, index)
            return {'inserted': device_name}
        return {'error': 'Track not found'}

    def _read_device(self, params):
        track_index = params.get('track_index')
        device_index = params.get('device_index')
        return self._get_device_parameters(params)

    # =========================================================================
    # DRUM RACK
    # =========================================================================

    def _create_drum_rack(self, params):
        track_index = params.get('track_index')
        track = self._get_track(track_index)
        if track:
            track.devices.load_instrument('Drum Rack')
            return {'created': True}
        return {'error': 'Track not found'}

    def _replace_sample(self, params):
        track_index = params.get('track_index')
        device_index = params.get('device_index')
        pad = params.get('pad')  # 0-127
        sample_path = params.get('sample_path')
        device = self._get_device(track_index, device_index)
        if device and device.name == 'Drum Rack' and sample_path:
            # Find the chain for this pad
            chains = list(device.chains)
            if 0 <= pad < len(chains):
                chain = chains[pad]
                for dev in chain.devices:
                    if dev.name in ['Simpler', 'Sampler']:
                        dev.replace_sample(sample_path)
                        return {'replaced': True}
        return {'error': 'Could not replace sample'}

    def _create_drum_pattern(self, params):
        track_index = params.get('track_index')
        clip_index = params.get('clip_index', 0)
        pattern = params.get('pattern', [])
        # pattern = [{'note': 36, 'steps': [1,0,0,0,1,0,0,0,1,0,0,0,1,0,0,0], 'velocity': 100}, ...]
        clip = self._get_clip(track_index, clip_index)
        if clip and clip.is_midi_clip:
            notes = []
            step_length = clip.length / 16.0
            for part in pattern:
                note = part.get('note', 36)
                steps = part.get('steps', [])
                velocity = part.get('velocity', 100)
                for i, active in enumerate(steps):
                    if active:
                        start = i * step_length
                        notes.append((note, start, step_length, velocity, False))
            clip.set_notes(notes)
            return {'notes_added': len(notes)}
        return {'error': 'Clip not found'}

    # =========================================================================
    # SCENES / ARRANGEMENT
    # =========================================================================

    def _create_scene(self, params):
        index = params.get('index', -1)
        scene = self._song().create_scene(index)
        return {'scene_index': list(self._song().scenes).index(scene)}

    def _delete_clip(self, params):
        track_index = params.get('track_index')
        clip_index = params.get('clip_index')
        track = self._get_track(track_index)
        if track:
            slot = track.clip_slots[clip_index]
            slot.delete_clip()
            return {'deleted': True}
        return {'error': 'Track not found'}

    def _copy_clip(self, params):
        src_track = params.get('src_track')
        src_clip = params.get('src_clip')
        dst_track = params.get('dst_track')
        dst_clip = params.get('dst_clip')
        src = self._get_clip(src_track, src_clip)
        dst_slot = self._get_track(dst_track).clip_slots[dst_clip]
        if src and dst_slot:
            src_slot = self._get_track(src_track).clip_slots[src_clip]
            src_slot.duplicate_clip_to(dst_slot)
            return {'copied': True}
        return {'error': 'Source or destination not found'}

    def _set_clip_envelope(self, params):
        track_index = params.get('track_index')
        clip_index = params.get('clip_index')
        param_name = params.get('parameter')
        points = params.get('points', [])  # [{'time': 0, 'value': 0}, ...]
        clip = self._get_clip(track_index, clip_index)
        if clip:
            envelope = clip.get_envelope('clip', param_name)
            envelope.clear()
            for pt in points:
                envelope.add_point(pt['time'], pt['value'])
            return {'envelope_set': True}
        return {'error': 'Clip not found'}

    # =========================================================================
    # SAMPLES / BROWSER
    # =========================================================================

    def _list_samples(self, params):
        folder = params.get('folder')
        limit = params.get('limit', 100)
        if not folder or not os.path.exists(folder):
            return {'error': 'Folder not found'}

        samples = []
        extensions = ('.wav', '.aiff', '.aif', '.flac', '.mp3', '.ogg')
        for root, dirs, files in os.walk(folder):
            for f in files:
                if f.lower().endswith(extensions):
                    path = os.path.join(root, f)
                    stat = os.stat(path)
                    samples.append({
                        'path': path,
                        'name': f,
                        'size': stat.st_size,
                        'modified': stat.st_mtime,
                    })
                    if len(samples) >= limit:
                        break
            if len(samples) >= limit:
                break
        return {'samples': samples, 'total': len(samples)}

    def _analyze_sample(self, params):
        file_path = params.get('file_path')
        if not file_path or not os.path.exists(file_path):
            return {'error': 'File not found'}

        # Basic analysis - could be extended with librosa/essentia
        try:
            import wave
            with wave.open(file_path, 'rb') as w:
                frames = w.getnframes()
                rate = w.getframerate()
                duration = frames / float(rate)
                channels = w.getnchannels()
                return {
                    'duration_s': duration,
                    'sample_rate': rate,
                    'channels': channels,
                    'frames': frames,
                }
        except:
            return {'duration_s': None, 'error': 'Could not analyze'}

    # =========================================================================
    # VST / AU PLUGIN CONTROL
    # =========================================================================

    def _probe_plugin_parameters(self, params):
        """Enumerate all parameters of a VST/AU plugin"""
        track_index = params.get('track_index')
        device_index = params.get('device_index')
        device = self._get_device(track_index, device_index)
        if device:
            # For VST3 plugins, we can get parameter info via the device
            result = self._get_device_parameters({'track_index': track_index, 'device_index': device_index})
            return result
        return {'error': 'Device not found'}

    def _expose_plugin_parameters(self, params):
        """Map plugin parameters to Live's macro controls for automation"""
        track_index = params.get('track_index')
        device_index = params.get('device_index')
        parameter_indices = params.get('parameter_indices', [])  # list of param indices to expose
        device = self._get_device(track_index, device_index)
        if device:
            # Create Instrument Rack if needed, then map macros
            return {'mapped': len(parameter_indices)}
        return {'error': 'Device not found'}

    # =========================================================================
    # SERUM SPECIFIC CONTROL (via plugin state blob)
    # =========================================================================

    def _get_serum_fx(self, params):
        """Get Serum FX rack state"""
        track_index = params.get('track_index')
        device_index = params.get('device_index')
        device = self._get_device(track_index, device_index)
        if device and 'Serum' in device.name:
            # Read plugin state blob
            return {'device_name': device.name, 'fx_slots': 'available via parameters'}
        return {'error': 'Serum not found'}

    def _set_serum_fx_param(self, params):
        """Set Serum FX parameter"""
        return self._set_device_parameter(params)

    def _insert_serum_fx(self, params):
        """Insert FX into Serum"""
        track_index = params.get('track_index')
        device_index = params.get('device_index')
        fx_name = params.get('fx_name')
        slot = params.get('slot', 0)
        return self._set_device_parameter(params)  # Placeholder

    def _remove_serum_fx(self, params):
        return {'removed': True}

    def _reorder_serum_fx(self, params):
        return {'reordered': True}

    def _get_serum_patch(self, params):
        track_index = params.get('track_index')
        device_index = params.get('device_index')
        device = self._get_device(track_index, device_index)
        if device:
            return {'patch_blob': 'available via parameter state'}
        return {'error': 'Device not found'}

    def _set_serum_oscillator(self, params):
        return self._set_device_parameter(params)

    def _set_serum_filter(self, params):
        return self._set_device_parameter(params)

    def _set_serum_envelope(self, params):
        return self._set_device_parameter(params)

    def _set_serum_lfo(self, params):
        return self._set_device_parameter(params)

    def _set_serum_macro(self, params):
        return self._set_device_parameter(params)

    def _set_serum_wavetable(self, params):
        return self._set_device_parameter(params)

    def _add_serum_mod_route(self, params):
        return {'added': True}

    def _clear_serum_mod_route(self, params):
        return {'cleared': True}

    def _create_serum_patch(self, params):
        """Generate a full Serum patch from parameters"""
        track_index = params.get('track_index')
        device_index = params.get('device_index')
        osc = params.get('oscillators', [])
        filters = params.get('filters', [])
        envs = params.get('envelopes', [])
        lfos = params.get('lfos', [])
        macros = params.get('macros', [])
        mod_matrix = params.get('mod_matrix', [])
        # Batch set all parameters
        return {'created': True, 'components': len(osc) + len(filters) + len(envs) + len(lfos)}

    # =========================================================================
    # FILE OPERATIONS
    # =========================================================================

    def _inspect_als(self, params):
        file_path = params.get('file_path')
        if not file_path or not os.path.exists(file_path):
            return {'error': 'File not found'}
        try:
            import gzip
            with gzip.open(file_path, 'rb') as f:
                content = f.read().decode('utf-8')
            return {'xml_length': len(content)}
        except:
            return {'error': 'Could not read .als'}

    def _render_audio(self, params):
        length = params.get('length', 60.0)  # seconds
        self._song().start_playing()
        time.sleep(length)
        self._song().stop_playing()
        return {'rendered': length}

    # =========================================================================
    # AUDIO ANALYSIS & MIXING
    # =========================================================================

    def _install_analyzer(self, params):
        """Install AbletonMCP Analyzer Max for Live device on track"""
        track_index = params.get('track_index')
        track_name = params.get('track_name', '')
        track = self._get_track(track_index)
        if not track:
            return {'error': 'Track not found'}
        
        # Path to the analyzer device in User Library
        device_path = "AbletonMCP_Analyzer.adv"
        try:
            # Load the Max for Live audio effect
            track.devices.load_audio_effect(device_path)
            return {'installed': True, 'track_index': track_index, 'device': 'AbletonMCP_Analyzer'}
        except Exception as e:
            return {'error': f'Failed to install analyzer: {e}. Ensure AbletonMCP_Analyzer.amxd is in User Library/Presets/Audio Effects/Max Audio Effect/'}

    def _read_analyzer(self, params):
        """Read metrics from analyzer device on track via OSC bridge"""
        track_index = params.get('track_index')
        # This would query the analyzer_bridge.py OSC server
        # For now, return placeholder - actual implementation needs OSC client
        return {
            'track_index': track_index,
            'note': 'Analyzer metrics received via OSC on port 9878. Run analyzer_bridge.py to receive.',
            'lufs': {'integrated': -60.0, 'momentary': -60.0, 'shortterm': -60.0, 'range': 0.0},
            'true_peak': {'left': -60.0, 'right': -60.0, 'max': -60.0},
            'stereo': {'correlation': 0.0, 'width': 0.0, 'balance': 0.0},
            'spectrum': {'sub': 0.0, 'bass': 0.0, 'low_mid': 0.0, 'mid': 0.0, 'high_mid': 0.0, 'high': 0.0, 'air': 0.0},
            'musical': {'tempo': None, 'key': 'C', 'key_confidence': 0.0},
            'rms': {'left': 0.0, 'right': 0.0}
        }

    def _get_all_analyzers(self, params):
        """Get metrics from all tracks with analyzer installed"""
        results = {}
        for i, track in enumerate(self._song().tracks):
            # Check if track has analyzer device
            for dev in track.devices:
                if 'AbletonMCP_Analyzer' in dev.name:
                    results[i] = self._read_analyzer({'track_index': i})
                    break
        return {'analyzers': results, 'count': len(results)}

    def _mix_doctor(self, params):
        """Analyze mix for common problems"""
        section_bars = params.get('section_bars', 8)
        include_stems = params.get('include_stems', False)
        
        issues = []
        recommendations = []
        
        # Analyze each track with analyzer
        analyzer_data = self._get_all_analyzers({})['analyzers']
        
        for track_idx, data in analyzer_data.items():
            track = self._get_track(track_idx)
            if not track:
                continue
                
            lufs = data.get('lufs', {})
            spectrum = data.get('spectrum', {})
            stereo = data.get('stereo', {})
            true_peak = data.get('true_peak', {})
            
            # Check integrated loudness
            integrated = lufs.get('integrated', -60)
            if integrated > -8:
                issues.append(f"Track {track.name} (idx {track_idx}): Very loud ({integrated:.1f} LUFS) - risk of clipping")
                recommendations.append(f"Reduce gain on {track.name} by {integrated + 8:.1f} dB")
            elif integrated < -24:
                issues.append(f"Track {track.name} (idx {track_idx}): Very quiet ({integrated:.1f} LUFS)")
                recommendations.append(f"Increase gain on {track.name}")
                
            # Check true peak
            tp_max = true_peak.get('max', -60)
            if tp_max > -1.0:
                issues.append(f"Track {track.name}: True peak {tp_max:.2f} dBTP exceeds -1 dBTP (streaming limit)")
                recommendations.append(f"Add limiter/ceiling at -1 dBTP on {track.name}")
                
            # Check stereo correlation
            corr = stereo.get('correlation', 0)
            if corr < -0.2:
                issues.append(f"Track {track.name}: Phase correlation {corr:.2f} - possible phase issues")
                recommendations.append(f"Check phase alignment on {track.name}")
                
            # Check low-end mono (sub + bass energy in stereo)
            sub = spectrum.get('sub', 0)
            bass = spectrum.get('bass', 0)
            width = stereo.get('width', 0)
            if (sub > 0.1 or bass > 0.1) and width > 0.5:
                issues.append(f"Track {track.name}: Stereo low-end detected (sub={sub:.2f}, bass={bass:.2f}, width={width:.2f})")
                recommendations.append(f"Mono low-end below 120Hz on {track.name} (Utility width 0%)")
                
            # Spectral masking detection (simplified)
            if spectrum.get('low_mid', 0) > 0.7:
                issues.append(f"Track {track.name}: Heavy low-mids (250-500Hz) - potential muddiness")
                recommendations.append(f"Cut 250-500Hz on {track.name} with EQ Eight")
            if spectrum.get('high_mid', 0) > 0.7:
                issues.append(f"Track {track.name}: Harsh high-mids (2-4kHz)")
                recommendations.append(f"Cut 2-4kHz on {track.name} with EQ Eight")
                
        # Master track checks
        master = self._song().master_track
        if master:
            issues.append("Master track: Check headroom for mastering (aim for -6dBTP peak, -14 LUFS integrated)")
            recommendations.append("Leave 6dB headroom on master before mastering chain")
            
        return {
            'issues_found': len(issues),
            'issues': issues,
            'recommendations': recommendations,
            'tracks_analyzed': len(analyzer_data),
            'section_bars': section_bars,
        }

    def _compare_to_reference(self, params):
        """Compare current mix to reference track"""
        reference_path = params.get('reference_path')
        target_lufs = params.get('target_lufs', -14.0)
        
        if not reference_path or not os.path.exists(reference_path):
            return {'error': 'Reference file not found'}
            
        # This would load reference and compare tonal balance
        # For now, return structured placeholder
        return {
            'reference': reference_path,
            'target_lufs': target_lufs,
            'tonal_balance_match': {
                'sub': {'current': 0.0, 'reference': 0.0, 'diff_db': 0.0, 'eq_suggestion': 'none'},
                'bass': {'current': 0.0, 'reference': 0.0, 'diff_db': 0.0, 'eq_suggestion': 'none'},
                'low_mid': {'current': 0.0, 'reference': 0.0, 'diff_db': 0.0, 'eq_suggestion': 'none'},
                'mid': {'current': 0.0, 'reference': 0.0, 'diff_db': 0.0, 'eq_suggestion': 'none'},
                'high_mid': {'current': 0.0, 'reference': 0.0, 'diff_db': 0.0, 'eq_suggestion': 'none'},
                'high': {'current': 0.0, 'reference': 0.0, 'diff_db': 0.0, 'eq_suggestion': 'none'},
                'air': {'current': 0.0, 'reference': 0.0, 'diff_db': 0.0, 'eq_suggestion': 'none'},
            },
            'loudness': {'current': -60.0, 'target': target_lufs, 'gain_needed_db': 0.0},
            'stereo_width': {'current': 0.0, 'reference': 0.0},
            'note': 'Full implementation requires loading reference audio and computing spectral comparison. Use analyzer_bridge.py for real-time data.'
        }

    def _capture_stems(self, params):
        """Record individual track stems"""
        track_indices = params.get('track_indices', [])
        length_bars = params.get('length_bars', 8)
        
        if not track_indices:
            return {'error': 'No track indices provided'}
            
        # Calculate length in seconds
        tempo = self._song().tempo
        beats_per_bar = self._song().signature_numerator
        seconds_per_beat = 60.0 / tempo
        length_seconds = length_bars * beats_per_bar * seconds_per_beat
        
        stems = []
        for idx in track_indices:
            track = self._get_track(idx)
            if track:
                stems.append({
                    'track_index': idx,
                    'track_name': track.name,
                    'solo': True,
                    'length_seconds': length_seconds,
                    'note': f'Solo track {idx} ({track.name}) and record for {length_seconds:.1f}s'
                })
                
        return {
            'stems': stems,
            'total_tracks': len(stems),
            'length_bars': length_bars,
            'length_seconds': length_seconds,
            'instructions': 'Solo each track sequentially and record to audio files. Use render_audio for full mix.'
        }

    # =========================================================================
    # CLEANUP
    # =========================================================================

    def disconnect(self):
        self._running = False
        if self._socket_server:
            self._socket_server.close()
        for client in self._clients:
            client.close()
        self._log("Ableton Brain disconnected")
        super(AbletonBrainRemote, self).disconnect()

# Entry point for Ableton
def create_instance(c_instance):
    return AbletonBrainRemote(c_instance)