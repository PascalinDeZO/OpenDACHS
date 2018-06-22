# standard library imports
# third party imports
import redis
# library specific imports


def explore(host, port, db=0):
    """Explore database.

    :param str host: host
    :param int port: port
    :param int db: database
    """
    try:
        strict_redis = redis.StrictRedis(host=host, port=port, db=db)
        msg = "{host}:{port} (db {db}):\t{key}:{value}"
        for key in strict_redis.keys():
            type_ = strict_redis.type(key)
            type_ = type_.decode("utf-8")
            if type_ == "string":
                value = strict_redis.get(key)
            elif type_ == "set":
                value = strict_redis.smembers(key)
            elif type_ == "list":
                value = strict_redis.lrange(key, 0, -1)
            elif type_ == "hash":
                value = strict_redis.hgetall(key)
            elif type_ == "zset":
                value = strict_redis.zrange(key, 0, -1)
            print(
                msg.format(host=host, port=port, db=db, key=key, value=value)
            )
            input(">:")
    except Exception:
        raise
    return


def main(host="localhost", port=6379):
    """main routine.

    :param str host: host
    :param int port: port
    :param int db: database
    """
    try:
        for db in range(0,16):
            explore(host, port, db=db)
    except Exception:
        raise
    return


if __name__ == "__main__":
    main()
