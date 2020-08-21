import graphene
from graphene import relay
from graphene_sqlalchemy import SQLAlchemyObjectType, SQLAlchemyConnectionField
from ruqqus.classes import Board as BoardModel, User as UserModel, Submission as SubmissionModel, \
    SubmissionAux as SubmissionAuxModel, Comment as CommentModel, CommentAux as CommentAuxModel
from ruqqus.__main__ import app, Base, db_session
from flask_graphql import GraphQLView


class Comment(SQLAlchemyObjectType):
    class Meta:
        model = SubmissionModel
        # abstract = True
        interfaces = (relay.Node,)

    comments_aux = graphene.List(lambda: CommentAux, id=graphene.String())

    def resolve_comments_aux(self, info, **kwargs):
        query = CommentAux.get_query(info)
        # query1 = Submission.get_query(info).first()
        query.filter_by(id=self.id).first()
        return query.filter_by(id=self.id).all()

    def resolve_submission(self, info, **kwargs):
        return CommentModel.filter_by(is_banned=False,
                                      is_deleted=False).all()

class CommentAux(SQLAlchemyObjectType):
    class Meta:
        model = CommentAuxModel
        interfaces = (relay.Node,)

    # comments_aux = graphene.List(lambda: Comm, id=graphene.String())
    def resolve_comment_aux(self, info, **kwargs):
        # query = SubmissionAux.get_query(info)
        # return query.filter_by(id=kwargs['id']).all()
        return CommentAuxModel.all()


class Submission(SQLAlchemyObjectType):
    class Meta:
        model = SubmissionModel
        # abstract = True
        interfaces = (relay.Node,)

    posts_aux = graphene.List(lambda: SubmissionAux, id=graphene.String())

    def resolve_posts_aux(self, info, **kwargs):
        query = SubmissionAux.get_query(info)
        return query.filter_by(id=self.id).all()

    def resolve_submission(self, info, **kwargs):
        return SubmissionModel.filter_by(is_banned=False,
                                         is_deleted=False,
                                         is_public=True).all()


class SubmissionAux(SQLAlchemyObjectType):
    class Meta:
        model = SubmissionAuxModel
        interfaces = (relay.Node,)

    # posts_aux = graphene.List(lambda: SubmissionAux, id=graphene.String())

    def resolve_submission_aux(self, info, **kwargs):
        # query = SubmissionAux.get_query(info)
        # return query.filter_by(id=kwargs['id']).all()
        return SubmissionAuxModel.all()


class User(SQLAlchemyObjectType):
    class Meta:
        model = UserModel
        interfaces = (relay.Node,)

        # only_fields = ('username', 'id','created_utc','admin_level','over_18')
        exclude_fields = (
            'passhash',
            'mfa_secret',
            'email',
            'delete_reason',
            'reddit_username',
            'patreon_id',
            'patreon_pledge_cents',
            'patreon_name',
            'patreon_access_token',
            'patreon_refresh_token'
        )

    posts = graphene.List(lambda: Submission)  # , id=graphene.String())
    comments = graphene.List(lambda: Comment)  # , id=graphene.String())

    def resolve_posts(self, info, **kwargs):
        query = Submission.get_query(info)
        return query.filter_by(author_id=self.id,
                               is_banned=False,
                               is_deleted=False).all()

    def resolve_comments(self, info, **kwargs):
        query = Comment.get_query(info)
        return query.filter_by(author_id=self.id,
                               is_banned=False,
                               is_deleted=False).all()


class Guild(SQLAlchemyObjectType):
    class Meta:
        model = BoardModel
        interfaces = (relay.Node,)

    def resolve_guilds(self, info, **kwargs):
        return BoardModel.fitler_by(is_private=False,
                                    is_banned=False
                                    ).all()

    posts = graphene.List(lambda: Submission,
                          id=graphene.String(),
                          sort=graphene.String(),
                          title=graphene.String(),
                          page=graphene.Int()
                          )

    def resolve_posts(self, info, **kwargs):

        page = 1
        if 'page' in kwargs:
            page = kwargs['page']

        query = Submission.get_query(info)
        query = query.join(Submission.submission_aux)

        if self.id:
            query = query.filter_by(board_id=self.id)\
                .filter(Submission.board_id == self.id)

        if self.name:
            query = query.filter_by(name=self.name)

        if 'id' in kwargs:
            query = query.filter_by(id=kwargs['id'])\
                .filter(Submission.author_id == kwargs['id'])

        if 'title' in kwargs:
            query = query.filter(SubmissionAux.title == kwargs['title'])

        if 'sort' in kwargs:
            sort = kwargs['sort']
            if sort == "hot":
                query = query.order_by(Submission.score_best.desc())
            elif sort == "new":
                query = query.order_by(Submission.created_utc.desc())
            elif sort == "disputed":
                query = query.order_by(Submission.score_disputed.desc())
            elif sort == "top":
                query = query.order_by(Submission.score_top.desc())
            elif sort == "activity":
                query = query.order_by(Submission.score_activity.desc())

        query.filter_by(is_banned=False,is_deleted=False)

        return [x[0] for x in query.offset(25*(page-1)).limit(26).all()]




# all_users = SQLAlchemyConnectionField(User.connection)
# all_posts = SQLAlchemyConnectionField(Submission.connection, sort=None)

class Query(graphene.ObjectType):
    node = relay.Node.Field()
    # Allows sorting over multiple columns, by default over the primary key
    guild = SQLAlchemyConnectionField(Guild.connection,
                                      id=graphene.String(),
                                      name=graphene.String()
                                      )

    user = SQLAlchemyConnectionField(User.connection,
                                     id=graphene.String(),
                                     username=graphene.String(),
                                     sort=graphene.String()
                                     )

    def resolve_guild(self, info, **kwargs):

        query = Guild.get_query(info)

        if "id" in kwargs:
            # print("id = ", kwargs['id'])
            query = query.filter_by(id=kwargs['id'])

        if 'name' in kwargs:
            query = query.filter_by(name=kwargs['name'])

        #if 'sort' in kwargs:
            #query

        return query.filter_by(is_private=False,
                               is_banned=False)


    def resolve_user(self, info, **kwargs):
        if "id" in kwargs:
            # print("id = ", kwargs['id'])
            query = User.get_query(info)
            return query.filter_by(id=kwargs['id'],
                                   is_private=False,
                                   is_banned=0,
                                   is_deleted=False).all()


    # Disable sorting over this field
    #all_guilds = SQLAlchemyConnectionField(Guild.connection, sort=None)




schema = graphene.Schema(query=Query)


"""check = query.filter_by(id=kwargs['id'], is_private=True).all()
            if check:
                return ['private user']"""
"""submission_aux = SQLAlchemyConnectionField(SubmissionAux.connection, sort=None)
    def resolve_submission_aux(self, info, **kwargs):
        if "id" in kwargs:
            # print("uname = ", kwargs['id'])
            query = SubmissionAux.get_query(info)
            return query.filter_by(id=kwargs['id']).all()"""
