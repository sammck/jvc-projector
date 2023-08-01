
'''
async def __call__(self, transport: JvcProjectorTransport) -> JvcResponse:
        logger.debug(f"Sending command {self}")
        basic_response_packet, advanced_response_packet = await transport.transact(self.command_packet)
        response = self.create_response(basic_response_packet, advanced_response_packet=advanced_response_packet)
        logger.debug(f"Received response {response}")
        return response
'''
