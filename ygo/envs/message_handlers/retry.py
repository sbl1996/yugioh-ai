from ygo.envs.glb import register_message
def msg_retry(self, buf):
	if self.verbose:
		print("retry")
	return buf[1:]

register_message({1: msg_retry})
