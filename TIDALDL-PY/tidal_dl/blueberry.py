class Blueberry (object):

    app_volume = 1.0
    break_loop = False

    @staticmethod
    def sel_local_vol(new_vol):
        Blueberry.app_volume = new_vol    
    @staticmethod
    def gel_local_vol():
        return Blueberry.app_volume
    @staticmethod
    def set_break_status(new_status):
        Blueberry.break_loop = new_status
    @staticmethod
    def should_break():
        return Blueberry.break_loop