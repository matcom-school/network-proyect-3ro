from .header_tcp import HeaderTCP
from random import randint

class Protocol_TCP:
    SMS = 0
    END = 1<<0
    SYS = 1<<1
    ACK = 1<<2
    EFE = 1<<3
    

    @staticmethod
    def __map_flack_to_response():
        return {
            Protocol_TCP.SMS : Protocol_TCP.ack_wich,
            Protocol_TCP.SYS : Protocol_TCP.sys_ack_to,
            Protocol_TCP.ACK | Protocol_TCP.SYS : Protocol_TCP.sys_end,
            Protocol_TCP.EFE : Protocol_TCP.ack_wich,
            Protocol_TCP.END : Protocol_TCP.end_with
        }

    @staticmethod
    def map_flack_to_response( msg) -> HeaderTCP:
        if type(msg) is bytes:
            flack = HeaderTCP.get( HeaderTCP.KEYW_FLACKS, msg)
        elif type(msg) is HeaderTCP:
            flack = msg.flacks
        else: raise TypeError
             
        return Protocol_TCP.__map_flack_to_response()[flack](msg)

    @staticmethod
    def __match_type(msg) -> ( HeaderTCP, str):
        if type(msg) is HeaderTCP: return msg, None
        if type(msg) is bytes : return HeaderTCP.descompose(msg)
        if type(msg) in [list,tuple] and len(msg) == 2: return HeaderTCP( source_port= msg[0], destination_post= msg[1]  ), None

        raise TypeError
    
    @staticmethod
    def sys_wich( msg) -> HeaderTCP :
        header,_ = Protocol_TCP.__match_type(msg)

        return  HeaderTCP(
            source_port= header.source_port,
            destination_post= header.destination_post,
            sequence_number= randint(1,1000),
            flacks=Protocol_TCP.SYS
        ) 

    @staticmethod
    def sys_ack_to( msg) -> HeaderTCP :
        header,_ = Protocol_TCP.__match_type(msg)

        return HeaderTCP(
            source_port= header.destination_post,
            destination_post= header.source_port,
            sequence_number= randint(1,1000),
            ack_number= header.sequence_number + 1,
            flacks= Protocol_TCP.ACK | Protocol_TCP.SYS
        )
    
    @staticmethod
    def sys_end( msg) -> HeaderTCP :
        header,_ = Protocol_TCP.__match_type(msg)

        return HeaderTCP(
            source_port= header.destination_post,
            destination_post= header.source_port,
            sequence_number= header.ack_number,
            ack_number= header.sequence_number + 1,
            flacks= Protocol_TCP.END | Protocol_TCP.SYS
        )
    
    @staticmethod
    def ack_wich( msg) -> HeaderTCP:
        if type(msg) is bytes:
            return HeaderTCP(
                source_port= HeaderTCP.get( HeaderTCP.KEYW_DESTINATION, msg),
                destination_post= HeaderTCP.get( HeaderTCP.KEYW_SOURCE, msg),
                sequence_number=HeaderTCP.get( HeaderTCP.KEYW_ACK, msg) + 1,
                ack_number= HeaderTCP.get( HeaderTCP.KEYW_SEQUENCE, msg),
                flacks= Protocol_TCP.ACK
            )
    @staticmethod
    def normal_sms( msg) -> HeaderTCP:
        header, _ = Protocol_TCP.__match_type( msg)

        return HeaderTCP(
            source_port= header.source_port,
            destination_post= header.destination_post,
            sequence_number= header.sequence_number,
            ack_number=header.ack_number,
            flacks= header.flacks,
            windows_size=header.windows_size,
        )
    @staticmethod
    def end_sms( msg ) -> HeaderTCP:
        header, _ = Protocol_TCP.__match_type( msg)

        return HeaderTCP(
            source_port= header.source_port,
            destination_post= header.destination_post,
            windows_size= 1,
            flacks= Protocol_TCP.END
        )
    @staticmethod
    def end_with( msg ) -> HeaderTCP:
        header, _ = Protocol_TCP.__match_type( msg)

        return HeaderTCP(
            source_port= header.destination_post,
            destination_post= header.source_port,
            ack_number= header.sequence_number,
            flacks= Protocol_TCP.ACK | Protocol_TCP.END,
            windows_size= 1
        )